"""PayPal checkout orchestration. Amount/currency always from the locked Orbiz order."""

from __future__ import annotations

import logging

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.common.exceptions import ConflictError, NotFoundError
from apps.orders.models import Order, OrderEvent
from apps.orders.services import mark_order_paid, mark_order_payment_failed
from apps.payments import paypal as paypal_client
from apps.payments.models import PaymentCheckout, PayPalWebhookEvent

logger = logging.getLogger(__name__)

ACTIVE_CHECKOUT_STATUSES = {
    PaymentCheckout.Status.CREATED,
    PaymentCheckout.Status.APPROVED,
}

CAPTURE_COMPLETED_EVENTS = {
    "PAYMENT.CAPTURE.COMPLETED",
    "CHECKOUT.ORDER.COMPLETED",
}

CAPTURE_FAILED_EVENTS = {
    "PAYMENT.CAPTURE.DENIED",
    "PAYMENT.CAPTURE.DECLINED",
    "CHECKOUT.PAYMENT-APPROVAL.REVERSED",
}


def _frontend_base() -> str:
    return (getattr(settings, "FRONTEND_URL", "") or "http://localhost:5173").rstrip("/")


def _return_urls(*, order: Order) -> tuple[str, str]:
    base = f"{_frontend_base()}/orders/{order.id}"
    return f"{base}?paypal=return", f"{base}?paypal=cancel"


def _lock_order(*, order_id: int, store_id: int | None = None) -> Order:
    qs = Order.objects.select_for_update().filter(pk=order_id)
    if store_id is not None:
        qs = qs.filter(store_id=store_id)
    order = qs.first()
    if order is None:
        raise NotFoundError("Order not found.")
    return order


def _record_order_note(*, order: Order, user, message: str) -> None:
    OrderEvent.objects.create(
        order=order,
        event_type=OrderEvent.EventType.NOTE,
        message=message,
        actor=user if getattr(user, "pk", None) else None,
    )


def latest_checkout(*, order: Order) -> PaymentCheckout | None:
    return (
        PaymentCheckout.objects.filter(order=order)
        .order_by("-created_at", "-id")
        .first()
    )


def get_checkout_for_store(*, order_id: int, store) -> PaymentCheckout | None:
    order = Order.objects.filter(pk=order_id, store=store).first()
    if order is None:
        raise NotFoundError("Order not found.")
    return latest_checkout(order=order)


@transaction.atomic
def create_checkout(*, order_id: int, store, user) -> PaymentCheckout:
    order = _lock_order(order_id=order_id, store_id=store.id)

    if order.fulfilment_status == Order.FulfilmentStatus.CANCELLED:
        raise ConflictError("Cannot create a checkout for a cancelled order.")
    if order.fulfilment_status == Order.FulfilmentStatus.DRAFT:
        raise ConflictError("Confirm the order before creating a PayPal checkout.")
    if order.payment_status == Order.PaymentStatus.PAID:
        raise ConflictError("Order is already paid.")
    if order.payment_status not in {
        Order.PaymentStatus.PENDING,
        Order.PaymentStatus.UNPAID,
        Order.PaymentStatus.FAILED,
        Order.PaymentStatus.CANCELLED,
    }:
        raise ConflictError(
            f"Cannot create checkout from payment status {order.payment_status}."
        )

    # Supersede any prior non-captured checkout.
    PaymentCheckout.objects.filter(
        order=order,
        status__in=ACTIVE_CHECKOUT_STATUSES,
    ).update(
        status=PaymentCheckout.Status.CANCELLED,
        updated_at=timezone.now(),
    )

    if order.payment_status != Order.PaymentStatus.PENDING:
        previous = order.payment_status
        order.payment_status = Order.PaymentStatus.PENDING
        order.save(update_fields=["payment_status", "updated_at"])
        OrderEvent.objects.create(
            order=order,
            event_type=OrderEvent.EventType.PAYMENT_STATUS_CHANGED,
            from_value=previous,
            to_value=Order.PaymentStatus.PENDING,
            message="Payment set to pending for PayPal Sandbox checkout.",
            actor=user,
        )

    return_url, cancel_url = _return_urls(order=order)
    created = paypal_client.create_order(
        amount=order.total,
        currency=order.currency,
        return_url=return_url,
        cancel_url=cancel_url,
        custom_id=str(order.id),
        reference_id=order.number,
    )

    checkout = PaymentCheckout.objects.create(
        order=order,
        paypal_order_id=created["id"],
        status=PaymentCheckout.Status.CREATED,
        approve_url=created.get("approve_url") or "",
        amount=order.total,
        currency=order.currency,
        is_sandbox=paypal_client.is_sandbox_mode(),
    )
    _record_order_note(
        order=order,
        user=user,
        message=f"PayPal Sandbox checkout created ({checkout.paypal_order_id}).",
    )
    return checkout


def capture_checkout(*, order_id: int, store, user) -> tuple[Order, PaymentCheckout]:
    with transaction.atomic():
        order = _lock_order(order_id=order_id, store_id=store.id)

        if order.payment_status == Order.PaymentStatus.PAID:
            checkout = latest_checkout(order=order)
            if checkout is None:
                raise ConflictError("Order is already paid but has no PayPal checkout.")
            return order, checkout

        checkout = (
            PaymentCheckout.objects.select_for_update()
            .filter(order=order)
            .exclude(status=PaymentCheckout.Status.CANCELLED)
            .order_by("-created_at", "-id")
            .first()
        )
        if checkout is None:
            raise ConflictError("Create a PayPal checkout before capturing.")
        if checkout.status == PaymentCheckout.Status.CAPTURED:
            order = mark_order_paid(
                order=order,
                user=user,
                message="Payment already captured via PayPal Sandbox.",
            )
            return order, checkout

        checkout_id = checkout.pk
        paypal_order_id = checkout.paypal_order_id

    # PayPal HTTP outside the lock so a raised error does not roll back failure writes.
    try:
        captured = paypal_client.capture_order(paypal_order_id=paypal_order_id)
    except Exception as exc:
        with transaction.atomic():
            order = _lock_order(order_id=order_id, store_id=store.id)
            checkout = PaymentCheckout.objects.select_for_update().get(pk=checkout_id)
            checkout.status = PaymentCheckout.Status.FAILED
            checkout.last_error = str(exc)[:2000]
            checkout.save(update_fields=["status", "last_error", "updated_at"])
            mark_order_payment_failed(
                order=order,
                user=user,
                message=f"PayPal Sandbox capture failed: {exc}",
            )
        raise

    status = (captured.get("status") or "").upper()
    capture_status = (captured.get("capture_status") or "").upper()
    completed = status == "COMPLETED" or capture_status == "COMPLETED"

    with transaction.atomic():
        order = _lock_order(order_id=order_id, store_id=store.id)
        checkout = PaymentCheckout.objects.select_for_update().get(pk=checkout_id)
        if not completed:
            checkout.status = PaymentCheckout.Status.FAILED
            checkout.last_error = f"Unexpected capture status: {status or capture_status}"
            checkout.save(update_fields=["status", "last_error", "updated_at"])
            order = mark_order_payment_failed(
                order=order,
                user=user,
                message=(
                    f"PayPal Sandbox capture not completed ({status or capture_status})."
                ),
            )
            raise ConflictError(checkout.last_error)

        checkout.status = PaymentCheckout.Status.CAPTURED
        checkout.capture_id = captured.get("capture_id") or ""
        checkout.last_error = ""
        checkout.save(
            update_fields=["status", "capture_id", "last_error", "updated_at"]
        )
        order = mark_order_paid(
            order=order,
            user=user,
            message=(
                "Paid via PayPal Sandbox capture "
                f"({checkout.capture_id or checkout.paypal_order_id})."
            ),
        )
        return order, checkout


def receive_webhook(*, event_id: str, event_type: str, payload: dict) -> PayPalWebhookEvent:
    """
    Persist a verified webhook event. Duplicate event_id returns the existing row.
    Caller must verify the signature before calling.
    """
    if not event_id:
        raise ConflictError("PayPal webhook is missing an event id.")
    try:
        with transaction.atomic():
            event = PayPalWebhookEvent.objects.create(
                event_id=event_id,
                event_type=event_type or "",
                payload=payload or {},
            )
    except IntegrityError:
        return PayPalWebhookEvent.objects.get(event_id=event_id)
    return event


@transaction.atomic
def process_webhook_event(*, event_pk: int) -> PayPalWebhookEvent:
    event = (
        PayPalWebhookEvent.objects.select_for_update()
        .filter(pk=event_pk)
        .first()
    )
    if event is None:
        raise NotFoundError("Webhook event not found.")
    if event.processed_at is not None:
        return event

    payload = event.payload or {}
    resource = payload.get("resource") or {}
    event_type = event.event_type or payload.get("event_type") or ""

    order = _resolve_order_from_resource(resource)
    if order is not None:
        event.order = order
        event.save(update_fields=["order"])

    if event_type in CAPTURE_COMPLETED_EVENTS or _resource_capture_completed(resource):
        if order is None:
            logger.warning(
                "PayPal webhook %s could not resolve Orbiz order", event.event_id
            )
        else:
            order = _lock_order(order_id=order.id)
            _mark_checkout_captured_from_webhook(order=order, resource=resource)
            mark_order_paid(
                order=order,
                user=None,
                message=f"Paid via PayPal Sandbox webhook ({event_type}).",
            )
    elif event_type in CAPTURE_FAILED_EVENTS:
        if order is not None:
            order = _lock_order(order_id=order.id)
            checkout = latest_checkout(order=order)
            if checkout and checkout.status != PaymentCheckout.Status.CAPTURED:
                checkout.status = PaymentCheckout.Status.FAILED
                checkout.last_error = f"Webhook: {event_type}"
                checkout.save(update_fields=["status", "last_error", "updated_at"])
            mark_order_payment_failed(
                order=order,
                user=None,
                message=f"PayPal Sandbox payment failed ({event_type}).",
            )

    event.processed_at = timezone.now()
    event.save(update_fields=["processed_at", "order"])
    return event


def _resource_capture_completed(resource: dict) -> bool:
    status = (resource.get("status") or "").upper()
    return status == "COMPLETED" and bool(resource.get("id"))


def _resolve_order_from_resource(resource: dict) -> Order | None:
    custom_id = resource.get("custom_id")
    if custom_id:
        try:
            order_id = int(str(custom_id))
        except (TypeError, ValueError):
            order_id = None
        if order_id:
            order = Order.objects.filter(pk=order_id).first()
            if order is not None:
                return order

    # Capture resource may nest supplementary_data / links; also try purchase_units.
    for unit in resource.get("purchase_units") or []:
        custom = unit.get("custom_id")
        if custom:
            try:
                order = Order.objects.filter(pk=int(str(custom))).first()
            except (TypeError, ValueError):
                order = None
            if order is not None:
                return order

    paypal_order_id = resource.get("supplementary_data", {}).get("related_ids", {}).get(
        "order_id"
    ) or resource.get("id")
    if paypal_order_id:
        checkout = (
            PaymentCheckout.objects.select_related("order")
            .filter(paypal_order_id=str(paypal_order_id))
            .first()
        )
        if checkout is not None:
            return checkout.order
        # Capture id path: find by capture_id later set; also match order id field on capture
        checkout = (
            PaymentCheckout.objects.select_related("order")
            .filter(capture_id=str(paypal_order_id))
            .first()
        )
        if checkout is not None:
            return checkout.order
    return None


def _mark_checkout_captured_from_webhook(*, order: Order, resource: dict) -> None:
    capture_id = str(resource.get("id") or "")
    related_order_id = (
        resource.get("supplementary_data", {})
        .get("related_ids", {})
        .get("order_id")
    )
    checkout = None
    if related_order_id:
        checkout = (
            PaymentCheckout.objects.select_for_update()
            .filter(order=order, paypal_order_id=str(related_order_id))
            .first()
        )
    if checkout is None:
        checkout = (
            PaymentCheckout.objects.select_for_update()
            .filter(order=order)
            .exclude(status=PaymentCheckout.Status.CANCELLED)
            .order_by("-created_at", "-id")
            .first()
        )
    if checkout is None:
        return
    checkout.status = PaymentCheckout.Status.CAPTURED
    if capture_id:
        checkout.capture_id = capture_id
    checkout.last_error = ""
    checkout.save(update_fields=["status", "capture_id", "last_error", "updated_at"])

"""PayPal orchestration: checkout, refunds, invoices, webhooks. Amounts always come from Orbiz rows."""

from __future__ import annotations

import logging
import secrets
from collections.abc import Callable
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone

from apps.common.exceptions import (
    ApplicationError,
    BadGatewayError,
    ConflictError,
    NotFoundError,
)
from apps.notifications.models import EmailLog, EmailStatus
from apps.notifications.services import queue_email
from apps.orders.models import Order, OrderEvent
from apps.orders.services import (
    MONEY_RECEIVED,
    PAID_LIKE,
    mark_order_paid,
    mark_order_payment_failed,
    mark_order_refunded,
)
from apps.payments import emails as payment_emails
from apps.payments import paypal as paypal_client
from apps.payments.models import (
    PaymentCheckout,
    PaymentInvoice,
    PaymentRefund,
    PayPalWebhookEvent,
)
from apps.stores.models import StoreMembership

logger = logging.getLogger(__name__)

ACTIVE_CHECKOUT_STATUSES = {
    PaymentCheckout.Status.CREATED,
    PaymentCheckout.Status.APPROVED,
}
ACTIVE_INVOICE_STATUSES = {
    PaymentInvoice.Status.DRAFT,
    PaymentInvoice.Status.SENT,
    PaymentInvoice.Status.SHARED,
}
PAID_INVOICE_STATUSES = {
    PaymentInvoice.Status.PAID,
    PaymentInvoice.Status.PARTIALLY_REFUNDED,
    PaymentInvoice.Status.REFUNDED,
}
# Refunds that reduce what is left to refund (a failed or cancelled one frees the amount).
COUNTED_REFUND_STATUSES = {
    PaymentRefund.Status.PENDING,
    PaymentRefund.Status.COMPLETED,
}

ALREADY_REFUNDED_MESSAGE = "This payment has already been fully refunded."

CAPTURE_COMPLETED_EVENTS = {
    "PAYMENT.CAPTURE.COMPLETED",
    "CHECKOUT.ORDER.COMPLETED",
}
CHECKOUT_APPROVED_EVENTS = {"CHECKOUT.ORDER.APPROVED"}
CAPTURE_FAILED_EVENTS = {
    "PAYMENT.CAPTURE.DENIED",
    "CHECKOUT.ORDER.DECLINED",
    "CHECKOUT.PAYMENT-APPROVAL.REVERSED",
}
REFUND_EVENTS = {
    "PAYMENT.CAPTURE.REFUNDED",
    "PAYMENT.CAPTURE.REVERSED",
    "PAYMENT.REFUND.PENDING",
    "PAYMENT.REFUND.FAILED",
}
INVOICE_EVENTS = {
    "INVOICING.INVOICE.PAID",
    "INVOICING.INVOICE.CANCELLED",
    "INVOICING.INVOICE.REFUNDED",
    "INVOICING.INVOICE.SENT",
    "INVOICING.INVOICE.UPDATED",
}

_REFUND_STATUS_FROM_PAYPAL = {
    "COMPLETED": PaymentRefund.Status.COMPLETED,
    "PENDING": PaymentRefund.Status.PENDING,
    "CANCELLED": PaymentRefund.Status.CANCELLED,
    "FAILED": PaymentRefund.Status.FAILED,
}
_REFUND_EVENT_DEFAULT_STATUS = {
    "PAYMENT.CAPTURE.REFUNDED": PaymentRefund.Status.COMPLETED,
    "PAYMENT.CAPTURE.REVERSED": PaymentRefund.Status.COMPLETED,
    "PAYMENT.REFUND.PENDING": PaymentRefund.Status.PENDING,
    "PAYMENT.REFUND.FAILED": PaymentRefund.Status.FAILED,
}
_PAID_INVOICE_STATUSES_AT_PAYPAL = {"PAID", "MARKED_AS_PAID"}
_INVOICE_STATUS_FROM_PAYPAL = {
    "REFUNDED": PaymentInvoice.Status.REFUNDED,
    "MARKED_AS_REFUNDED": PaymentInvoice.Status.REFUNDED,
    "PARTIALLY_REFUNDED": PaymentInvoice.Status.PARTIALLY_REFUNDED,
    "CANCELLED": PaymentInvoice.Status.CANCELLED,
}


def _frontend_base() -> str:
    return (getattr(settings, "FRONTEND_URL", "") or "http://localhost:5173").rstrip("/")


def _return_urls(*, order: Order) -> tuple[str, str]:
    # A public page: the buyer who pays from an emailed link has no Orbiz login. It forwards
    # a signed-in seller to the order (where the return triggers the capture fallback).
    base = f"{_frontend_base()}/pay/return?order={order.id}"
    return f"{base}&paypal=return", f"{base}&paypal=cancel"


def _lock_order(*, order_id: int, store_id: int | None = None) -> Order:
    qs = Order.objects.select_for_update().filter(pk=order_id)
    if store_id is not None:
        qs = qs.filter(store_id=store_id)
    order = qs.first()
    if order is None:
        raise NotFoundError("Order not found.")
    return order


def _record_order_event(*, order: Order, event_type: str, user, message: str) -> None:
    OrderEvent.objects.create(
        order=order,
        event_type=event_type,
        message=message,
        actor=user if getattr(user, "pk", None) else None,
    )


def _record_order_note(*, order: Order, user, message: str) -> None:
    _record_order_event(
        order=order, event_type=OrderEvent.EventType.NOTE, user=user, message=message
    )


def is_currency_supported(currency: str) -> bool:
    return currency.upper() in settings.PAYPAL_SUPPORTED_CURRENCIES


def _require_supported_currency(order: Order) -> None:
    if not is_currency_supported(order.currency):
        supported = ", ".join(settings.PAYPAL_SUPPORTED_CURRENCIES)
        raise ConflictError(
            f"PayPal Sandbox can't take {order.currency} payments — "
            f"use an order in {supported}."
        )


def _require_payable(order: Order, *, noun: str) -> None:
    """Guard shared by every way of asking the buyer to pay (checkout, invoice)."""
    if order.fulfilment_status == Order.FulfilmentStatus.CANCELLED:
        raise ConflictError(f"Cannot create a {noun} for a cancelled order.")
    if order.fulfilment_status == Order.FulfilmentStatus.DRAFT:
        raise ConflictError(f"Confirm the order before creating a PayPal {noun}.")
    if order.payment_status in MONEY_RECEIVED:
        raise ConflictError("Order is already paid.")


def _cancel_active_checkouts(order: Order) -> None:
    PaymentCheckout.objects.filter(
        order=order,
        status__in=ACTIVE_CHECKOUT_STATUSES,
    ).update(
        status=PaymentCheckout.Status.CANCELLED,
        updated_at=timezone.now(),
    )


def _set_payment_pending(*, order: Order, user, message: str) -> None:
    if order.payment_status == Order.PaymentStatus.PENDING:
        return
    previous = order.payment_status
    order.payment_status = Order.PaymentStatus.PENDING
    order.save(update_fields=["payment_status", "updated_at"])
    OrderEvent.objects.create(
        order=order,
        event_type=OrderEvent.EventType.PAYMENT_STATUS_CHANGED,
        from_value=previous,
        to_value=Order.PaymentStatus.PENDING,
        message=message,
        actor=user,
    )


def latest_checkout(*, order: Order) -> PaymentCheckout | None:
    return (
        PaymentCheckout.objects.filter(order=order)
        .order_by("-created_at", "-id")
        .first()
    )


def latest_invoice(*, order: Order) -> PaymentInvoice | None:
    return (
        PaymentInvoice.objects.filter(order=order)
        .order_by("-created_at", "-id")
        .first()
    )


def get_checkout_for_store(*, order_id: int, store) -> PaymentCheckout | None:
    order = Order.objects.filter(pk=order_id, store=store).first()
    if order is None:
        raise NotFoundError("Order not found.")
    return latest_checkout(order=order)


# --- Checkout -----------------------------------------------------------------------


@transaction.atomic
def create_checkout(*, order_id: int, store, user) -> PaymentCheckout:
    order = _lock_order(order_id=order_id, store_id=store.id)

    _require_payable(order, noun="checkout")
    _require_supported_currency(order)

    # One open payment request per order: supersede checkouts and any open invoice.
    _cancel_active_checkouts(order)
    _cancel_open_invoices(order=order, user=user)
    _set_payment_pending(
        order=order,
        user=user,
        message="Payment set to pending for PayPal Sandbox checkout.",
    )

    return_url, cancel_url = _return_urls(order=order)
    created = paypal_client.create_order(
        amount=order.total,
        currency=order.currency,
        return_url=return_url,
        cancel_url=cancel_url,
        custom_id=str(order.id),
        reference_id=order.number,
        items=[
            {
                "name": line.product_name,
                "quantity": line.quantity,
                "unit_price": line.unit_price,
                "sku": line.sku,
            }
            for line in order.lines.all()
        ],
        description=f"{store.name} - order {order.number}",
        # Shown in the buyer's PayPal history and emails. PayPal refuses a repeated value per
        # merchant, so each checkout gets its own suffix (a rebuilt dev database reuses numbers).
        invoice_id=f"{order.number}-{secrets.token_hex(3).upper()}",
        brand_name=store.name,
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


def _capture_at_paypal(paypal_order_id: str) -> dict:
    """Capture, or read the existing capture when PayPal says it already happened."""
    try:
        return paypal_client.capture_order(paypal_order_id=paypal_order_id)
    except BadGatewayError as exc:
        # The buyer's return and the approval webhook both capture; the loser lands here.
        if exc.extra.get("paypal_issue") != paypal_client.ORDER_ALREADY_CAPTURED:
            raise
    existing = paypal_client.get_order(paypal_order_id=paypal_order_id)
    return paypal_client.capture_summary(existing, paypal_order_id=paypal_order_id)


def capture_checkout(*, order_id: int, store, user) -> tuple[Order, PaymentCheckout]:
    with transaction.atomic():
        order = _lock_order(order_id=order_id, store_id=store.id)

        if order.payment_status in MONEY_RECEIVED:
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
            order = _mark_paid_and_notify(
                order=order,
                user=user,
                message="Payment already captured via PayPal Sandbox.",
                via="PayPal checkout",
            )
            return order, checkout

        checkout_id = checkout.pk
        paypal_order_id = checkout.paypal_order_id

    # PayPal HTTP outside the lock so a raised error does not roll back failure writes.
    try:
        captured = _capture_at_paypal(paypal_order_id)
    except Exception as exc:
        if (
            isinstance(exc, BadGatewayError)
            and exc.extra.get("paypal_issue") == paypal_client.ORDER_NOT_APPROVED
        ):
            # Not a failure: the buyer simply hasn't approved yet, so the checkout stays open
            # and the order stays as it is. Capturing again after approval works.
            raise ConflictError(exc.message, code="order_not_approved") from exc
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
        order = _mark_paid_and_notify(
            order=order,
            user=user,
            message=(
                "Paid via PayPal Sandbox capture "
                f"({checkout.capture_id or checkout.paypal_order_id})."
            ),
            via="PayPal checkout",
        )
        return order, checkout


# --- Refunds ------------------------------------------------------------------------


def _paid_source(*, order: Order) -> tuple[str, Decimal, str] | None:
    """(capture id, paid amount, currency) of the PayPal payment that settled the order."""
    checkout = (
        PaymentCheckout.objects.filter(order=order, status=PaymentCheckout.Status.CAPTURED)
        .exclude(capture_id="")
        .order_by("-created_at", "-id")
        .first()
    )
    if checkout is not None:
        return checkout.capture_id, checkout.amount, checkout.currency
    invoice = (
        PaymentInvoice.objects.filter(order=order, status__in=PAID_INVOICE_STATUSES)
        .exclude(capture_id="")
        .order_by("-created_at", "-id")
        .first()
    )
    if invoice is not None:
        return invoice.capture_id, invoice.amount, invoice.currency
    return None


def _refunded_total(*, order: Order, capture_id: str) -> Decimal:
    total = PaymentRefund.objects.filter(
        order=order,
        capture_id=capture_id,
        status__in=COUNTED_REFUND_STATUSES,
    ).aggregate(total=Sum("amount"))["total"]
    return total or Decimal("0.00")


def get_refundable_amount(*, order: Order) -> Decimal:
    """What the seller can still refund on this order through PayPal (0 when nothing)."""
    source = _paid_source(order=order)
    if source is None or order.payment_status not in PAID_LIKE:
        return Decimal("0.00")
    capture_id, paid_amount, _currency = source
    return max(paid_amount - _refunded_total(order=order, capture_id=capture_id), Decimal("0.00"))


def _apply_refund_to_order(
    *, order: Order, refund: PaymentRefund, paid_amount: Decimal, user
) -> Order:
    fully = _refunded_total(order=order, capture_id=refund.capture_id) >= paid_amount
    origin = " (from the PayPal dashboard)" if refund.source == PaymentRefund.Source.PAYPAL else ""
    order = mark_order_refunded(
        order=order,
        user=user,
        fully=fully,
        message=(
            f"Refunded {refund.currency} {refund.amount} via PayPal Sandbox{origin}. "
            f"Order {'fully' if fully else 'partially'} refunded."
        ),
    )
    _notify_buyer(
        order=order,
        user=user,
        key=f"refund:{refund.pk}",
        kind="refund_notice",
        render=lambda store: payment_emails.render_refund_notice(
            order=order,
            store=store,
            sandbox=paypal_client.is_sandbox_mode(),
            amount=refund.amount,
            currency=refund.currency,
            fully=fully,
        ),
    )
    return order


def _fail_refund(*, refund_pk: int, error: str) -> None:
    with transaction.atomic():
        refund = PaymentRefund.objects.select_for_update().get(pk=refund_pk)
        refund.status = PaymentRefund.Status.FAILED
        refund.last_error = error[:2000]
        refund.save(update_fields=["status", "last_error", "updated_at"])


def refund_order(
    *,
    order_id: int,
    store,
    user,
    amount: Decimal | None = None,
    note_to_payer: str = "",
) -> Order:
    """Refund an order's PayPal payment. `amount=None` refunds everything still refundable."""
    with transaction.atomic():
        order = _lock_order(order_id=order_id, store_id=store.id)
        if order.payment_status == Order.PaymentStatus.REFUNDED:
            raise ConflictError(ALREADY_REFUNDED_MESSAGE)
        if order.payment_status not in PAID_LIKE:
            raise ConflictError("Only a paid order can be refunded.")
        source = _paid_source(order=order)
        if source is None:
            raise ConflictError(
                "This order was marked paid offline — there is no PayPal payment to refund."
            )
        capture_id, paid_amount, currency = source
        refundable = paid_amount - _refunded_total(order=order, capture_id=capture_id)
        if refundable <= 0:
            raise ConflictError(ALREADY_REFUNDED_MESSAGE)
        refund_amount = refundable if amount is None else amount
        if refund_amount > refundable:
            raise ConflictError(
                f"Only {currency} {refundable} is left to refund on this order."
            )
        # The pending row reserves the amount, so a concurrent refund cannot exceed it.
        refund = PaymentRefund.objects.create(
            order=order,
            capture_id=capture_id,
            amount=refund_amount,
            currency=currency,
            note_to_payer=note_to_payer.strip(),
            actor=user,
        )

    # PayPal HTTP outside the lock; the request id makes a retry replay, not repeat.
    try:
        result = paypal_client.refund_capture(
            capture_id=capture_id,
            amount=refund_amount,
            currency=currency,
            note_to_payer=refund.note_to_payer,
            request_id=str(refund.request_id),
        )
    except Exception as exc:
        _fail_refund(refund_pk=refund.pk, error=str(exc))
        raise

    paypal_status = _REFUND_STATUS_FROM_PAYPAL.get(
        result["status"], PaymentRefund.Status.PENDING
    )
    with transaction.atomic():
        order = _lock_order(order_id=order_id, store_id=store.id)
        refund = PaymentRefund.objects.select_for_update().get(pk=refund.pk)
        # The refund webhook may already have claimed this row; then there is nothing to do.
        if refund.paypal_refund_id != result["id"]:
            refund.paypal_refund_id = result["id"]
            refund.status = paypal_status
            refund.last_error = ""
            refund.save(
                update_fields=["paypal_refund_id", "status", "last_error", "updated_at"]
            )
            if paypal_status in COUNTED_REFUND_STATUSES:
                order = _apply_refund_to_order(
                    order=order, refund=refund, paid_amount=paid_amount, user=user
                )

    if paypal_status not in COUNTED_REFUND_STATUSES:
        raise ConflictError(
            f"PayPal did not complete the refund ({result['status'].lower() or 'unknown'})."
        )
    return order


# --- Invoices -----------------------------------------------------------------------


def _open_invoices(*, order: Order):
    return PaymentInvoice.objects.select_for_update().filter(
        order=order, status__in=ACTIVE_INVOICE_STATUSES
    )


def _cancel_invoice(*, order: Order, invoice: PaymentInvoice, user) -> None:
    # A draft was never sent, so there is nothing to cancel at PayPal.
    if invoice.status != PaymentInvoice.Status.DRAFT and invoice.paypal_invoice_id:
        try:
            paypal_client.cancel_invoice(invoice_id=invoice.paypal_invoice_id)
        except BadGatewayError as exc:
            issue = exc.extra.get("paypal_issue")
            if issue == "CANNOT_CANCEL_PAID_INVOICE":
                raise ConflictError(
                    "PayPal reports this invoice is already paid — it will sync shortly."
                ) from exc
            if issue != "INVOICE_CANCELED_ALREADY":
                raise
    invoice.status = PaymentInvoice.Status.CANCELLED
    invoice.save(update_fields=["status", "updated_at"])
    _record_order_event(
        order=order,
        event_type=OrderEvent.EventType.INVOICE_CANCELLED,
        user=user,
        message=f"PayPal Sandbox invoice {invoice.invoice_number} cancelled.",
    )


def _cancel_open_invoices(*, order: Order, user) -> int:
    cancelled = 0
    for invoice in _open_invoices(order=order):
        _cancel_invoice(order=order, invoice=invoice, user=user)
        cancelled += 1
    return cancelled


def _next_invoice_number(*, order: Order) -> str:
    # Unique across stores sharing one merchant account; PayPal allows 25 characters.
    sequence = PaymentInvoice.objects.filter(order=order).count() + 1
    return f"ORB-{order.id}-{sequence}"


def send_invoice_for_order(
    *, order_id: int, store, user, recipient_email: str = ""
) -> PaymentInvoice:
    """
    Create and send a PayPal invoice for the order total.

    With a recipient email the buyer is emailed — by Orbiz (PAYPAL_INVOICE_DELIVERY=orbiz,
    the PayPal invoice is then link-only so nobody is emailed twice) or by PayPal itself.
    Without an email the invoice is payable by link only and nothing is emailed.
    """
    email = recipient_email.strip().lower()
    orbiz_emails = bool(email) and settings.PAYPAL_INVOICE_DELIVERY == "orbiz"
    paypal_emails = bool(email) and not orbiz_emails

    with transaction.atomic():
        order = _lock_order(order_id=order_id, store_id=store.id)
        _require_payable(order, noun="invoice")
        _require_supported_currency(order)

        _cancel_active_checkouts(order)
        _cancel_open_invoices(order=order, user=user)

        invoice = PaymentInvoice.objects.create(
            order=order,
            invoice_number=_next_invoice_number(order=order),
            recipient_email=email,
            amount=order.total,
            currency=order.currency,
            is_sandbox=paypal_client.is_sandbox_mode(),
        )
        items = [
            {
                "name": line.product_name,
                "quantity": line.quantity,
                "unit_price": line.unit_price,
            }
            for line in order.lines.all()
        ]
        customer_name = order.customer.name

    # PayPal HTTP outside the lock; a failed attempt is kept as a FAILED row.
    paypal_invoice_id = ""
    try:
        created = paypal_client.create_invoice(
            invoice_number=invoice.invoice_number,
            reference=f"orbiz-order:{order_id}",
            currency=invoice.currency,
            items=items,
            note=f"Order {order.number}",
            recipient_email=email,
            recipient_name=customer_name,
            request_id=str(invoice.request_id),
        )
        paypal_invoice_id = created["id"]
        paypal_client.send_invoice(invoice_id=paypal_invoice_id, send_to_recipient=paypal_emails)
        remote = paypal_client.get_invoice(invoice_id=paypal_invoice_id)
        if orbiz_emails and not paypal_client.invoice_payer_url(remote):
            raise BadGatewayError("PayPal did not return an invoice link to email.")
    except Exception as exc:
        with transaction.atomic():
            invoice = PaymentInvoice.objects.select_for_update().get(pk=invoice.pk)
            invoice.paypal_invoice_id = paypal_invoice_id or None
            invoice.status = PaymentInvoice.Status.FAILED
            invoice.last_error = str(exc)[:2000]
            invoice.save(
                update_fields=["paypal_invoice_id", "status", "last_error", "updated_at"]
            )
        raise

    with transaction.atomic():
        order = _lock_order(order_id=order_id, store_id=store.id)
        invoice = PaymentInvoice.objects.select_for_update().get(pk=invoice.pk)
        invoice.paypal_invoice_id = paypal_invoice_id
        invoice.status = (
            PaymentInvoice.Status.SENT if email else PaymentInvoice.Status.SHARED
        )
        invoice.delivered_via = (
            PaymentInvoice.Delivery.ORBIZ
            if orbiz_emails
            else PaymentInvoice.Delivery.PAYPAL
            if paypal_emails
            else PaymentInvoice.Delivery.NONE
        )
        invoice.recipient_view_url = paypal_client.invoice_payer_url(remote)
        invoice.sent_at = timezone.now()
        invoice.last_error = ""
        invoice.save(
            update_fields=[
                "paypal_invoice_id",
                "status",
                "delivered_via",
                "recipient_view_url",
                "sent_at",
                "last_error",
                "updated_at",
            ]
        )
        _set_payment_pending(
            order=order,
            user=user,
            message="Payment set to pending for PayPal Sandbox invoice.",
        )
        if orbiz_emails:
            _queue_payment_email(
                order=order,
                store=store,
                user=user,
                recipient=email,
                link=invoice.recipient_view_url,
                key=f"invoice:{invoice.invoice_number}",
                invoice_number=invoice.invoice_number,
                issued_on=timezone.localdate(invoice.created_at),
            )
        _record_order_event(
            order=order,
            event_type=OrderEvent.EventType.INVOICE_SENT,
            user=user,
            message=(
                f"PayPal Sandbox invoice {invoice.invoice_number} emailed to {email}"
                f"{' by Orbiz' if orbiz_emails else ''}."
                if email
                else (
                    f"PayPal Sandbox invoice {invoice.invoice_number} created as a "
                    "shareable link (no email sent)."
                )
            ),
        )
    return invoice


@transaction.atomic
def cancel_invoice_for_order(*, order_id: int, store, user) -> PaymentInvoice:
    order = _lock_order(order_id=order_id, store_id=store.id)
    if _cancel_open_invoices(order=order, user=user) == 0:
        raise ConflictError("There is no open PayPal invoice to cancel.")
    return latest_invoice(order=order)


# --- Payment-link emails ------------------------------------------------------------


def _payment_email_reference(*, order: Order, key: str) -> str:
    return f"order:{order.id}:{key}"


def _queue_notice(
    *,
    order: Order,
    recipients: list[str],
    key: str,
    kind: str,
    render,
    from_email: str,
    reply_to: str = "",
) -> None:
    """
    Queue a notice email once per `key` on the order.

    Best effort: this runs inside payment, refund and confirm processing, so a missing address
    or any failure here is logged and never rolls the business action back.
    """
    if not recipients:
        logger.info("No recipient for the %s notice on order %s; skipped.", kind, order.id)
        return
    reference = _payment_email_reference(order=order, key=key)
    try:
        with transaction.atomic():
            if EmailLog.objects.filter(reference=reference).exists():
                return
            rendered = render(order.store)
            queue_email(
                to=recipients,
                subject=rendered.subject,
                body=rendered.text,
                html_body=rendered.html,
                from_email=from_email,
                reply_to=reply_to,
                reference=reference,
                kind=kind,
            )
    except Exception:
        logger.exception("Could not queue the %s email for order %s.", kind, order.id)


def _notify_buyer(*, order: Order, user, key: str, kind: str, render) -> None:
    """Email the order's customer a notice (receipt, refund, confirmation), once per `key`."""
    customer_email = (order.customer.email or "").strip()
    _queue_notice(
        order=order,
        recipients=[customer_email] if customer_email else [],
        key=key,
        kind=kind,
        render=render,
        from_email=payment_emails.sender_for(order.store),
        reply_to=getattr(user, "email", "") or "",
    )


def _notify_sellers(*, order: Order, via: str) -> None:
    """Tell the store's members a payment landed, once per order."""
    if not settings.NOTIFY_SELLER_ON_PAYMENT:
        return
    emails = {
        membership.user.email.strip().lower()
        for membership in StoreMembership.objects.filter(store_id=order.store_id).select_related(
            "user"
        )
        if membership.user.email
    }
    _queue_notice(
        order=order,
        recipients=sorted(emails),
        key="paid:seller",
        kind="seller_payment_notice",
        render=lambda store: payment_emails.render_seller_payment_notice(
            order=order,
            store=store,
            sandbox=paypal_client.is_sandbox_mode(),
            via=via,
            order_url=f"{_frontend_base()}/orders/{order.id}",
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
    )


def _mark_paid_and_notify(*, order: Order, user, message: str, via: str = "PayPal") -> Order:
    """mark_order_paid, plus a buyer receipt and a seller notice the first time it is paid."""
    was_paid = order.payment_status in MONEY_RECEIVED
    order = mark_order_paid(order=order, user=user, message=message)
    if not was_paid:
        _notify_buyer(
            order=order,
            user=user,
            key="paid",
            kind="payment_receipt",
            render=lambda store: payment_emails.render_payment_receipt(
                order=order, store=store, sandbox=paypal_client.is_sandbox_mode()
            ),
        )
        _notify_sellers(order=order, via=via)
    return order


def notify_order_confirmed(*, order: Order, user) -> None:
    """The opt-in "order confirmed" email to the customer (the seller ticks it on confirm)."""
    _notify_buyer(
        order=order,
        user=user,
        key="confirmed",
        kind="order_confirmation",
        render=lambda store: payment_emails.render_order_confirmation(
            order=order, store=store, sandbox=paypal_client.is_sandbox_mode()
        ),
    )


def _queue_payment_email(
    *,
    order: Order,
    store,
    user,
    recipient: str,
    link: str,
    key: str,
    kind: str = payment_emails.REQUEST,
    invoice_number: str = "",
    issued_on=None,
) -> EmailLog:
    """Queue the buyer's payment email; it is sent by the Celery worker after commit."""
    rendered = payment_emails.render_payment_request(
        order=order,
        store=store,
        link=link,
        # `key` is "invoice:<number>" or "checkout:<paypal order id>".
        link_kind=(
            payment_emails.INVOICE_LINK
            if key.startswith("invoice:")
            else payment_emails.CHECKOUT_LINK
        ),
        kind=kind,
        sandbox=paypal_client.is_sandbox_mode(),
        invoice_number=invoice_number,
        issued_on=issued_on,
    )
    return queue_email(
        to=recipient,
        subject=rendered.subject,
        body=rendered.text,
        html_body=rendered.html,
        from_email=payment_emails.sender_for(store),
        # Replies reach the seller who asked for the payment, not the shared sender address.
        reply_to=getattr(user, "email", "") or "",
        reference=_payment_email_reference(order=order, key=key),
        kind="payment_reminder" if kind == payment_emails.REMINDER else "payment_request",
    )[0]


def _open_request_invoice(*, order: Order) -> PaymentInvoice | None:
    return (
        PaymentInvoice.objects.filter(
            order=order,
            status__in={PaymentInvoice.Status.SENT, PaymentInvoice.Status.SHARED},
        )
        .order_by("-created_at", "-id")
        .first()
    )


def _open_request_checkout(*, order: Order) -> PaymentCheckout | None:
    return (
        PaymentCheckout.objects.filter(order=order, status__in=ACTIVE_CHECKOUT_STATUSES)
        .order_by("-created_at", "-id")
        .first()
    )


def _current_payment_request(*, order: Order) -> tuple[str, str, str]:
    """(link, reference key, label) of the one open PayPal payment request."""
    invoice = _open_request_invoice(order=order)
    if invoice is not None and invoice.recipient_view_url:
        return (
            invoice.recipient_view_url,
            f"invoice:{invoice.invoice_number}",
            f"invoice {invoice.invoice_number}",
        )
    checkout = _open_request_checkout(order=order)
    if checkout is not None and checkout.approve_url:
        return checkout.approve_url, f"checkout:{checkout.paypal_order_id}", "checkout link"
    raise ConflictError("Create a PayPal checkout or invoice before emailing a payment link.")


def payment_request_summary(*, order: Order) -> dict:
    """What the seller's UI shows for the order's single open PayPal payment request."""
    summary = {
        "kind": "none",
        "status": "",
        "url": "",
        "recipient_email": "",
        "delivered_via": "",
        "last_emailed_at": None,
        "last_email_status": "",
        "last_email_error": "",
        "can_email": False,
        "delivery_mode": settings.PAYPAL_INVOICE_DELIVERY,
    }
    if order.payment_status in MONEY_RECEIVED:
        return summary

    invoice = _open_request_invoice(order=order)
    checkout = None if invoice is not None else _open_request_checkout(order=order)
    if invoice is not None and invoice.recipient_view_url:
        summary.update(
            kind="invoice",
            status=invoice.status,
            url=invoice.recipient_view_url,
            recipient_email=invoice.recipient_email,
            delivered_via=invoice.delivered_via,
        )
        key = f"invoice:{invoice.invoice_number}"
    elif checkout is not None and checkout.approve_url:
        summary.update(kind="checkout", status=checkout.status, url=checkout.approve_url)
        key = f"checkout:{checkout.paypal_order_id}"
    else:
        return summary

    summary["can_email"] = True
    last = (
        EmailLog.objects.filter(reference=_payment_email_reference(order=order, key=key))
        .order_by("-created_at", "-id")
        .first()
    )
    if last is not None:
        summary.update(
            recipient_email=summary["recipient_email"] or last.recipient,
            last_emailed_at=last.created_at,
            last_email_status=last.status,
            last_email_error=last.error_message,
        )
    return summary


def email_payment_link(
    *,
    order_id: int,
    store,
    user,
    recipient_email: str = "",
    kind: str = payment_emails.REQUEST,
) -> EmailLog:
    """
    Email the order's current open PayPal payment link (invoice or checkout) to the buyer.

    Nothing is sent for a paid order, without an open request, or twice to the same
    address within PAYMENT_EMAIL_COOLDOWN_SECONDS. A checkout link older than
    PAYPAL_CHECKOUT_LINK_MAX_AGE_HOURS is replaced by a fresh one first.
    """
    order = Order.objects.filter(pk=order_id, store=store).first()
    if order is None:
        raise NotFoundError("Order not found.")

    # Stale checkout links are replaced before locking: create_checkout talks to PayPal.
    if _open_request_invoice(order=order) is None:
        checkout = _open_request_checkout(order=order)
        max_age = timedelta(hours=settings.PAYPAL_CHECKOUT_LINK_MAX_AGE_HOURS)
        if checkout is not None and timezone.now() - checkout.created_at > max_age:
            create_checkout(order_id=order_id, store=store, user=user)

    with transaction.atomic():
        order = _lock_order(order_id=order_id, store_id=store.id)
        if order.payment_status in MONEY_RECEIVED:
            raise ConflictError("Order is already paid.")

        email = (recipient_email or order.customer.email or "").strip().lower()
        if not email:
            raise ApplicationError(
                "Enter an email address — this customer has none on file.",
                code="recipient_required",
            )

        link, key, label = _current_payment_request(order=order)
        reference = _payment_email_reference(order=order, key=key)
        cooldown = timedelta(seconds=settings.PAYMENT_EMAIL_COOLDOWN_SECONDS)
        recent = (
            EmailLog.objects.filter(
                reference=reference,
                recipient=email,
                created_at__gte=timezone.now() - cooldown,
            )
            .exclude(status=EmailStatus.FAILED)
            .order_by("-created_at")
            .first()
        )
        if recent is not None:
            wait = max(1, int((recent.created_at + cooldown - timezone.now()).total_seconds()))
            raise ConflictError(
                f"A payment link was just emailed to {email}. Try again in {wait} seconds.",
                code="email_cooldown",
                extra={"retry_after_seconds": wait},
            )

        invoice = _open_request_invoice(order=order)
        log = _queue_payment_email(
            order=order,
            store=store,
            user=user,
            recipient=email,
            link=link,
            key=key,
            kind=kind,
            invoice_number=invoice.invoice_number if invoice else "",
            issued_on=timezone.localdate(invoice.created_at) if invoice else None,
        )
        if invoice is not None:
            # Emailing a link-only invoice turns it into one the buyer has been sent.
            invoice.recipient_email = email
            if invoice.status == PaymentInvoice.Status.SHARED:
                invoice.status = PaymentInvoice.Status.SENT
            if invoice.delivered_via == PaymentInvoice.Delivery.NONE:
                invoice.delivered_via = PaymentInvoice.Delivery.ORBIZ
            invoice.save(
                update_fields=["recipient_email", "status", "delivered_via", "updated_at"]
            )
        noun = "reminder" if kind == payment_emails.REMINDER else "request"
        _record_order_event(
            order=order,
            event_type=OrderEvent.EventType.PAYMENT_LINK_EMAILED,
            user=user,
            message=f"Payment {noun} emailed to {email} ({label}).",
        )
    return log


# --- Webhooks -----------------------------------------------------------------------


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


def process_webhook_event(*, event_pk: int) -> PayPalWebhookEvent:
    event = PayPalWebhookEvent.objects.filter(pk=event_pk).first()
    if event is None:
        raise NotFoundError("Webhook event not found.")
    if event.processed_at is not None:
        return event

    payload = event.payload or {}
    resource = payload.get("resource") or {}
    event_type = event.event_type or payload.get("event_type") or ""
    # PayPal HTTP before any lock: the fetched invoice, not the payload, is the truth.
    remote_invoice = (
        _fetch_remote_invoice(resource) if event_type in INVOICE_EVENTS else None
    )

    follow_up: Callable[[], None] | None = None
    with transaction.atomic():
        event = PayPalWebhookEvent.objects.select_for_update().get(pk=event_pk)
        if event.processed_at is not None:
            return event

        order = _resolve_order_from_resource(resource)
        if order is not None:
            event.order = order
        try:
            with transaction.atomic():
                follow_up = _dispatch_webhook_event(
                    event_type=event_type,
                    resource=resource,
                    order=order,
                    remote_invoice=remote_invoice,
                )
        except ConflictError as exc:
            # State already moved on (e.g. a cancelled order): surface it, don't retry.
            logger.warning(
                "PayPal webhook %s not applied: %s", event.event_id, exc.message
            )
            if order is not None:
                _record_order_note(
                    order=order,
                    user=None,
                    message=f"PayPal webhook {event_type} could not be applied: {exc.message}",
                )

        event.processed_at = timezone.now()
        event.save(update_fields=["processed_at", "order"])

    if follow_up is not None:
        follow_up()
    return event


def _dispatch_webhook_event(
    *,
    event_type: str,
    resource: dict,
    order: Order | None,
    remote_invoice: dict | None,
) -> Callable[[], None] | None:
    """Apply one event. Returns work to run after the transaction commits, if any."""
    if event_type in CAPTURE_COMPLETED_EVENTS:
        _handle_capture_completed(order=order, resource=resource, event_type=event_type)
    elif event_type in CHECKOUT_APPROVED_EVENTS:
        return _handle_checkout_approved(order=order, resource=resource)
    elif event_type in CAPTURE_FAILED_EVENTS:
        _handle_payment_failed(order=order, event_type=event_type)
    elif event_type in REFUND_EVENTS:
        _handle_refund_event(order=order, resource=resource, event_type=event_type)
    elif event_type in INVOICE_EVENTS:
        _handle_invoice_event(remote=remote_invoice)
    return None


def _handle_capture_completed(*, order: Order | None, resource: dict, event_type: str) -> None:
    if order is None:
        logger.warning("PayPal %s could not resolve an Orbiz order", event_type)
        return
    order = _lock_order(order_id=order.id)
    _mark_checkout_captured_from_webhook(order=order, resource=resource)
    _mark_paid_and_notify(
        order=order,
        user=None,
        message=f"Paid via PayPal Sandbox webhook ({event_type}).",
    )


def _handle_payment_failed(*, order: Order | None, event_type: str) -> None:
    if order is None:
        return
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


def _handle_checkout_approved(
    *, order: Order | None, resource: dict
) -> Callable[[], None] | None:
    """Record the buyer's approval, then capture on the server so a closed tab still pays."""
    if order is None:
        logger.warning("PayPal CHECKOUT.ORDER.APPROVED could not resolve an Orbiz order")
        return None
    order = _lock_order(order_id=order.id)
    checkout = (
        PaymentCheckout.objects.select_for_update()
        .filter(order=order, paypal_order_id=str(resource.get("id") or ""))
        .first()
    )
    # A superseded or finished checkout must never be captured.
    if checkout is None or checkout.status not in ACTIVE_CHECKOUT_STATUSES:
        return None
    if checkout.status == PaymentCheckout.Status.CREATED:
        checkout.status = PaymentCheckout.Status.APPROVED
        checkout.save(update_fields=["status", "updated_at"])
        _record_order_event(
            order=order,
            event_type=OrderEvent.EventType.PAYMENT_APPROVED,
            user=None,
            message="Buyer approved the PayPal Sandbox payment.",
        )
    store = order.store
    return lambda: _auto_capture(order_id=order.id, store=store)


def _auto_capture(*, order_id: int, store) -> None:
    try:
        capture_checkout(order_id=order_id, store=store, user=None)
    except ApplicationError as exc:
        # capture_checkout already recorded the failure on the checkout and the order.
        logger.warning("PayPal auto-capture failed order=%s: %s", order_id, exc.message)


def _claim_pending_refund(*, order: Order, amount: Decimal) -> PaymentRefund | None:
    """Our own refund whose API response has not been stored yet (webhook raced it)."""
    return (
        PaymentRefund.objects.select_for_update()
        .filter(
            order=order,
            source=PaymentRefund.Source.ORBIZ,
            status=PaymentRefund.Status.PENDING,
            paypal_refund_id__isnull=True,
            amount=amount,
        )
        .order_by("created_at", "id")
        .first()
    )


def _amount_from_resource(resource: dict) -> Decimal | None:
    value = (resource.get("amount") or {}).get("value")
    if value is None:
        return None
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None
    return amount if amount > 0 else None


def _handle_refund_event(*, order: Order | None, resource: dict, event_type: str) -> None:
    """Sync a refund (ours, or one made in the PayPal dashboard) onto the order."""
    refund_id = str(resource.get("id") or "")
    if not refund_id:
        logger.warning("PayPal %s carried no refund id", event_type)
        return
    status = _REFUND_STATUS_FROM_PAYPAL.get(
        (resource.get("status") or "").upper()
    ) or _REFUND_EVENT_DEFAULT_STATUS[event_type]

    refund = PaymentRefund.objects.select_for_update().filter(paypal_refund_id=refund_id).first()
    # A stored paypal_refund_id means the order already reflects this refund (if counted).
    already_applied = refund is not None and refund.status in COUNTED_REFUND_STATUSES
    if refund is not None:
        order = _lock_order(order_id=refund.order_id)
    elif order is not None:
        order = _lock_order(order_id=order.id)
    else:
        logger.warning("PayPal %s %s could not resolve an Orbiz order", event_type, refund_id)
        return

    source = _paid_source(order=order)
    if source is None:
        logger.warning("PayPal %s %s: order has no PayPal payment", event_type, refund_id)
        return
    capture_id, paid_amount, currency = source

    if refund is None:
        amount = _amount_from_resource(resource)
        if amount is None:
            logger.warning("PayPal %s %s carried no amount", event_type, refund_id)
            return
        refund = _claim_pending_refund(order=order, amount=amount) or PaymentRefund(
            order=order,
            capture_id=capture_id,
            currency=currency,
            amount=amount,
            source=PaymentRefund.Source.PAYPAL,
        )
    refund.paypal_refund_id = refund_id
    refund.status = status
    refund.save()
    if status in COUNTED_REFUND_STATUSES and not already_applied:
        _apply_refund_to_order(order=order, refund=refund, paid_amount=paid_amount, user=None)


def _fetch_remote_invoice(resource: dict) -> dict | None:
    invoice_id = str((resource.get("invoice") or {}).get("id") or resource.get("id") or "")
    if not invoice_id or not PaymentInvoice.objects.filter(paypal_invoice_id=invoice_id).exists():
        return None
    return paypal_client.get_invoice(invoice_id=invoice_id)


def _handle_invoice_event(*, remote: dict | None) -> None:
    if remote is None:
        return
    invoice = (
        PaymentInvoice.objects.select_for_update()
        .filter(paypal_invoice_id=str(remote.get("id") or ""))
        .first()
    )
    if invoice is None:
        return
    order = _lock_order(order_id=invoice.order_id)
    paypal_status = (remote.get("status") or "").upper()

    if paypal_status in _PAID_INVOICE_STATUSES_AT_PAYPAL:
        invoice.status = PaymentInvoice.Status.PAID
        invoice.capture_id = paypal_client.invoice_payment_id(remote) or invoice.capture_id
        invoice.paid_at = invoice.paid_at or timezone.now()
        invoice.last_error = ""
        invoice.save(
            update_fields=["status", "capture_id", "paid_at", "last_error", "updated_at"]
        )
        _mark_paid_and_notify(
            order=order,
            user=None,
            message=f"Paid via PayPal Sandbox invoice {invoice.invoice_number}.",
            via=f"PayPal invoice {invoice.invoice_number}",
        )
        return

    new_status = _INVOICE_STATUS_FROM_PAYPAL.get(paypal_status)
    if new_status is None or new_status == invoice.status:
        return
    # A cancellation only applies to an invoice that is still open.
    if new_status == PaymentInvoice.Status.CANCELLED and invoice.status not in ACTIVE_INVOICE_STATUSES:
        return
    invoice.status = new_status
    invoice.save(update_fields=["status", "updated_at"])
    if new_status == PaymentInvoice.Status.CANCELLED:
        _record_order_event(
            order=order,
            event_type=OrderEvent.EventType.INVOICE_CANCELLED,
            user=None,
            message=f"PayPal Sandbox invoice {invoice.invoice_number} cancelled on PayPal.",
        )


def _related_paypal_order_id(resource: dict) -> str:
    related = (resource.get("supplementary_data") or {}).get("related_ids") or {}
    return str(related.get("order_id") or "")


def _capture_id_from_links(resource: dict) -> str:
    """A refund's `up` link points at the capture it refunds."""
    for link in resource.get("links") or []:
        if (link.get("rel") or "") == "up" and "/captures/" in (link.get("href") or ""):
            return link["href"].rstrip("/").rsplit("/", 1)[-1]
    return ""


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

    paypal_order_id = _related_paypal_order_id(resource) or str(resource.get("id") or "")
    if paypal_order_id:
        checkout = (
            PaymentCheckout.objects.select_related("order")
            .filter(paypal_order_id=paypal_order_id)
            .first()
        )
        if checkout is not None:
            return checkout.order
        # Capture id path: find by capture_id later set; also match order id field on capture
        checkout = (
            PaymentCheckout.objects.select_related("order")
            .filter(capture_id=paypal_order_id)
            .first()
        )
        if checkout is not None:
            return checkout.order

    # Invoice payments: the invoice itself, its number on a capture, or a refund's capture.
    invoice_id = str((resource.get("invoice") or {}).get("id") or resource.get("id") or "")
    capture_id = _capture_id_from_links(resource)
    invoice_number = str(resource.get("invoice_id") or "")
    invoice = (
        PaymentInvoice.objects.select_related("order")
        .filter(paypal_invoice_id=invoice_id)
        .first()
        if invoice_id
        else None
    )
    if invoice is None and invoice_number:
        invoice = (
            PaymentInvoice.objects.select_related("order")
            .filter(invoice_number=invoice_number)
            .first()
        )
    if invoice is None and capture_id:
        checkout = (
            PaymentCheckout.objects.select_related("order")
            .filter(capture_id=capture_id)
            .first()
        )
        if checkout is not None:
            return checkout.order
        invoice = (
            PaymentInvoice.objects.select_related("order")
            .filter(capture_id=capture_id)
            .first()
        )
    return invoice.order if invoice is not None else None


def _mark_checkout_captured_from_webhook(*, order: Order, resource: dict) -> None:
    capture_id = str(resource.get("id") or "")
    related_order_id = _related_paypal_order_id(resource)
    checkout = None
    if related_order_id:
        checkout = (
            PaymentCheckout.objects.select_for_update()
            .filter(order=order, paypal_order_id=related_order_id)
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

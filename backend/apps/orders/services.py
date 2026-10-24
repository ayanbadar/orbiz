from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.common.exceptions import ConflictError
from apps.customers.models import Customer
from apps.orders.models import Order, OrderEvent, OrderLine
from apps.products.models import Product
from apps.products.services import adjust_stock, check_stock
from apps.stores.models import Store

# fulfilment_status → allowed next fulfilment statuses (excluding cancel, handled separately)
FULFILMENT_TRANSITIONS: dict[str, set[str]] = {
    Order.FulfilmentStatus.DRAFT: set(),  # only via confirm/cancel
    Order.FulfilmentStatus.UNFULFILLED: {Order.FulfilmentStatus.PROCESSING},
    Order.FulfilmentStatus.PROCESSING: {Order.FulfilmentStatus.SHIPPED},
    Order.FulfilmentStatus.SHIPPED: {Order.FulfilmentStatus.COMPLETED},
    Order.FulfilmentStatus.COMPLETED: set(),
    Order.FulfilmentStatus.CANCELLED: set(),
}

CANCELABLE = {
    Order.FulfilmentStatus.DRAFT,
    Order.FulfilmentStatus.UNFULFILLED,
    Order.FulfilmentStatus.PROCESSING,
    Order.FulfilmentStatus.SHIPPED,
}

# Fulfilment steps that move physical ops forward — require paid unless allow_unpaid.
PAYMENT_REQUIRED_TARGETS = {
    Order.FulfilmentStatus.PROCESSING,
    Order.FulfilmentStatus.SHIPPED,
    Order.FulfilmentStatus.COMPLETED,
}


def _next_order_number(*, store) -> str:
    """Allocate the next ORD-N under an already-locked store row."""
    latest = (
        Order.objects.filter(store=store, number__startswith="ORD-")
        .order_by("-id")
        .values_list("number", flat=True)
        .first()
    )
    if latest:
        try:
            n = int(str(latest).split("-", 1)[1])
        except (IndexError, ValueError):
            n = 1000
    else:
        n = 1000
    return f"ORD-{n + 1}"


def _lock_products(*, store, product_ids: list[int]) -> dict[int, Product]:
    """Lock products in pk order to avoid deadlocks across concurrent orders."""
    ids = sorted({pk for pk in product_ids if pk is not None})
    if not ids:
        return {}
    return {
        p.pk: p
        for p in Product.objects.select_for_update()
        .filter(pk__in=ids, store=store)
        .order_by("pk")
    }


def _record_event(
    *,
    order: Order,
    event_type: str,
    actor,
    message: str = "",
    from_value: str = "",
    to_value: str = "",
) -> OrderEvent:
    return OrderEvent.objects.create(
        order=order,
        event_type=event_type,
        from_value=from_value,
        to_value=to_value,
        message=message,
        actor=actor,
    )


def _resolve_lines(*, store, lines: list[dict]) -> list[dict]:
    if not lines:
        raise ValidationError({"lines": "Add at least one line."})

    seen: set[int] = set()
    resolved: list[dict] = []
    for raw in lines:
        product_id = raw["product_id"]
        quantity = raw["quantity"]
        if product_id in seen:
            raise ValidationError({"lines": "Each product may only appear once per order."})
        seen.add(product_id)
        try:
            product = Product.objects.get(pk=product_id, store=store)
        except Product.DoesNotExist as exc:
            raise ValidationError({"lines": f"Product {product_id} was not found in this store."}) from exc
        if not product.is_active:
            raise ValidationError({"lines": f"{product.sku} is inactive and cannot be sold."})
        if quantity < 1:
            raise ValidationError({"lines": "Quantity must be at least 1."})
        unit_price = product.price
        line_total = (unit_price * quantity).quantize(Decimal("0.01"))
        resolved.append(
            {
                "product": product,
                "product_name": product.name,
                "sku": product.sku,
                "unit_price": unit_price,
                "quantity": quantity,
                "line_total": line_total,
            }
        )
    return resolved


def _totals(resolved: list[dict]) -> Decimal:
    total = sum((row["line_total"] for row in resolved), Decimal("0.00"))
    return total.quantize(Decimal("0.01"))


def _replace_lines(*, order: Order, resolved: list[dict]) -> None:
    order.lines.all().delete()
    OrderLine.objects.bulk_create(
        [
            OrderLine(
                order=order,
                product=row["product"],
                product_name=row["product_name"],
                sku=row["sku"],
                unit_price=row["unit_price"],
                quantity=row["quantity"],
                line_total=row["line_total"],
            )
            for row in resolved
        ]
    )
    subtotal = _totals(resolved)
    order.subtotal = subtotal
    order.total = subtotal
    order.save(update_fields=["subtotal", "total", "updated_at"])


@transaction.atomic
def create_draft(
    *,
    store,
    user,
    customer: Customer,
    lines: list[dict],
    delivery_notes: str = "",
    internal_notes: str = "",
    source_message: str = "",
) -> Order:
    if customer.store_id != store.id:
        raise ValidationError({"customer_id": "Customer belongs to another store."})
    # Serialize number allocation per store (matches products' IntegrityError → Conflict).
    store = Store.objects.select_for_update().get(pk=store.pk)
    resolved = _resolve_lines(store=store, lines=lines)
    order = None
    last_exc: IntegrityError | None = None
    for _ in range(3):
        try:
            order = Order.objects.create(
                store=store,
                number=_next_order_number(store=store),
                customer=customer,
                fulfilment_status=Order.FulfilmentStatus.DRAFT,
                payment_status=Order.PaymentStatus.UNPAID,
                currency=store.currency,
                delivery_notes=(delivery_notes or "").strip(),
                internal_notes=(internal_notes or "").strip(),
                source_message=(source_message or "").strip(),
                created_by=user,
            )
            break
        except IntegrityError as exc:
            last_exc = exc
            continue
    if order is None:
        raise ConflictError("Could not allocate a unique order number.") from last_exc
    _replace_lines(order=order, resolved=resolved)
    _record_event(
        order=order,
        event_type=OrderEvent.EventType.CREATED,
        actor=user,
        message=f"Draft {order.number} created.",
        to_value=Order.FulfilmentStatus.DRAFT,
    )
    return order


@transaction.atomic
def update_draft(
    *,
    order: Order,
    user,
    customer: Customer | None = None,
    lines: list[dict] | None = None,
    delivery_notes: str | None = None,
    internal_notes: str | None = None,
    source_message: str | None = None,
) -> Order:
    if order.fulfilment_status != Order.FulfilmentStatus.DRAFT:
        raise ConflictError("Only draft orders can be edited.")
    if customer is not None:
        if customer.store_id != order.store_id:
            raise ValidationError({"customer_id": "Customer belongs to another store."})
        order.customer = customer
    if delivery_notes is not None:
        order.delivery_notes = delivery_notes.strip()
    if internal_notes is not None:
        order.internal_notes = internal_notes.strip()
    if source_message is not None:
        order.source_message = source_message.strip()
    order.save()
    if lines is not None:
        resolved = _resolve_lines(store=order.store, lines=lines)
        _replace_lines(order=order, resolved=resolved)
    _record_event(
        order=order,
        event_type=OrderEvent.EventType.UPDATED,
        actor=user,
        message=f"Draft {order.number} updated.",
    )
    return order


def _lock_order(order: Order) -> Order:
    return Order.objects.select_for_update().get(pk=order.pk)


@transaction.atomic
def confirm_order(*, order: Order, user) -> Order:
    order = _lock_order(order)
    if order.fulfilment_status != Order.FulfilmentStatus.DRAFT:
        raise ConflictError("Only draft orders can be confirmed.")

    lines = list(order.lines.select_related("product"))
    if not lines:
        raise ValidationError({"lines": "Add at least one line before confirming."})

    product_ids = [line.product_id for line in lines]
    locked = _lock_products(store=order.store, product_ids=product_ids)
    for line in lines:
        product = locked.get(line.product_id)
        if product is None:
            raise ValidationError({"lines": f"Product for {line.sku} is no longer available."})
        check_stock(product=product, quantity=line.quantity)

    for line in lines:
        product = locked[line.product_id]
        adjust_stock(
            product=product,
            delta=-line.quantity,
            reason=f"sale:{order.number}",
            user=user,
            already_locked=True,
        )

    previous = order.fulfilment_status
    order.fulfilment_status = Order.FulfilmentStatus.UNFULFILLED
    order.payment_status = Order.PaymentStatus.PENDING
    order.stock_deducted = True
    order.confirmed_at = timezone.now()
    order.save(
        update_fields=[
            "fulfilment_status",
            "payment_status",
            "stock_deducted",
            "confirmed_at",
            "updated_at",
        ]
    )
    _record_event(
        order=order,
        event_type=OrderEvent.EventType.CONFIRMED,
        actor=user,
        message="Order confirmed; stock deducted.",
        from_value=previous,
        to_value=order.fulfilment_status,
    )
    _record_event(
        order=order,
        event_type=OrderEvent.EventType.PAYMENT_STATUS_CHANGED,
        actor=user,
        message="Payment set to pending (awaiting PayPal Sandbox in §2.7).",
        from_value=Order.PaymentStatus.UNPAID,
        to_value=Order.PaymentStatus.PENDING,
    )
    return order


@transaction.atomic
def transition_fulfilment(
    *,
    order: Order,
    user,
    fulfilment_status: str,
    allow_unpaid: bool = False,
) -> Order:
    """
    Advance fulfilment along the allow-list.

    By default, processing / shipped / completed require payment_status=paid.
    Pass allow_unpaid=True only for an explicit policy (e.g. COD) — never silently.
    """
    order = _lock_order(order)
    allowed = FULFILMENT_TRANSITIONS.get(order.fulfilment_status, set())
    if fulfilment_status not in allowed:
        raise ConflictError(
            f"Cannot move from {order.fulfilment_status} to {fulfilment_status}."
        )
    if (
        fulfilment_status in PAYMENT_REQUIRED_TARGETS
        and order.payment_status != Order.PaymentStatus.PAID
        and not allow_unpaid
    ):
        raise ConflictError(
            "Payment must be paid before advancing fulfilment. "
            "Use allow_unpaid only for an explicit unpaid policy (e.g. COD)."
        )
    previous = order.fulfilment_status
    order.fulfilment_status = fulfilment_status
    order.save(update_fields=["fulfilment_status", "updated_at"])
    message = f"Fulfilment status changed to {fulfilment_status}."
    if allow_unpaid and order.payment_status != Order.PaymentStatus.PAID:
        message += " (allow_unpaid override)"
    _record_event(
        order=order,
        event_type=OrderEvent.EventType.STATUS_CHANGED,
        actor=user,
        message=message,
        from_value=previous,
        to_value=fulfilment_status,
    )
    return order


@transaction.atomic
def mark_order_paid(*, order: Order, user, message: str = "") -> Order:
    """
    Set order-level payment to paid (seed / tests / future verified PayPal webhook).

    Does not change fulfilment. Rejects cancelled orders and already-paid no-ops
    as conflicts when not pending/unpaid/failed/cancelled-attempt.
    """
    order = _lock_order(order)
    if order.fulfilment_status == Order.FulfilmentStatus.CANCELLED:
        raise ConflictError("Cannot mark a cancelled order as paid.")
    if order.payment_status == Order.PaymentStatus.PAID:
        return order
    if order.payment_status not in {
        Order.PaymentStatus.PENDING,
        Order.PaymentStatus.UNPAID,
        Order.PaymentStatus.FAILED,
        Order.PaymentStatus.CANCELLED,
    }:
        raise ConflictError(
            f"Cannot mark payment paid from status {order.payment_status}."
        )
    previous = order.payment_status
    order.payment_status = Order.PaymentStatus.PAID
    order.save(update_fields=["payment_status", "updated_at"])
    _record_event(
        order=order,
        event_type=OrderEvent.EventType.PAYMENT_STATUS_CHANGED,
        actor=user,
        message=message or "Payment marked paid.",
        from_value=previous,
        to_value=Order.PaymentStatus.PAID,
    )
    return order


@transaction.atomic
def abandon_payment(*, order: Order, user) -> Order:
    """
    Abandon the current payment attempt without cancelling the order.

    Order stays unfulfilled so the seller can retry checkout or cancel separately.
    """
    order = _lock_order(order)
    if order.fulfilment_status != Order.FulfilmentStatus.UNFULFILLED:
        raise ConflictError(
            "Only unfulfilled orders can abandon a payment attempt."
        )
    if order.payment_status != Order.PaymentStatus.PENDING:
        raise ConflictError(
            "Only a pending payment attempt can be abandoned."
        )
    previous = order.payment_status
    order.payment_status = Order.PaymentStatus.CANCELLED
    order.save(update_fields=["payment_status", "updated_at"])
    _record_event(
        order=order,
        event_type=OrderEvent.EventType.PAYMENT_STATUS_CHANGED,
        actor=user,
        message="Payment attempt abandoned; order remains unfulfilled for retry or cancel.",
        from_value=previous,
        to_value=Order.PaymentStatus.CANCELLED,
    )
    return order


@transaction.atomic
def cancel_order(*, order: Order, user) -> Order:
    order = _lock_order(order)
    if order.fulfilment_status == Order.FulfilmentStatus.CANCELLED:
        raise ConflictError("Order is already cancelled.")
    if order.fulfilment_status not in CANCELABLE:
        raise ConflictError("This order cannot be cancelled.")

    previous_fulfilment = order.fulfilment_status
    previous_payment = order.payment_status
    should_restore = order.stock_deducted

    if should_restore:
        lines = list(order.lines.select_related("product"))
        product_ids = [line.product_id for line in lines]
        locked = _lock_products(store=order.store, product_ids=product_ids)
        for line in lines:
            product = locked.get(line.product_id)
            if product is None:
                raise ValidationError(
                    {
                        "lines": (
                            f"Cannot restore stock for {line.sku}: "
                            "product is no longer available in this store."
                        )
                    }
                )
            adjust_stock(
                product=product,
                delta=line.quantity,
                reason=f"cancel-restore:{order.number}",
                user=user,
                already_locked=True,
            )
        order.stock_deducted = False

    order.fulfilment_status = Order.FulfilmentStatus.CANCELLED
    # Order cancel closes open money state; abandoned-checkout alone uses abandon_payment.
    if order.payment_status in {
        Order.PaymentStatus.UNPAID,
        Order.PaymentStatus.PENDING,
    }:
        order.payment_status = Order.PaymentStatus.CANCELLED
    order.cancelled_at = timezone.now()
    order.save(
        update_fields=[
            "fulfilment_status",
            "payment_status",
            "stock_deducted",
            "cancelled_at",
            "updated_at",
        ]
    )
    _record_event(
        order=order,
        event_type=OrderEvent.EventType.CANCELLED,
        actor=user,
        message="Order cancelled."
        + (" Stock restored." if should_restore else ""),
        from_value=previous_fulfilment,
        to_value=Order.FulfilmentStatus.CANCELLED,
    )
    if previous_payment != order.payment_status:
        _record_event(
            order=order,
            event_type=OrderEvent.EventType.PAYMENT_STATUS_CHANGED,
            actor=user,
            message="Payment status set to cancelled with the order.",
            from_value=previous_payment,
            to_value=order.payment_status,
        )
    return order


def recent_usage_for_product(*, product: Product, limit: int = 20) -> list[dict]:
    """Recent non-draft order lines for a product (product detail hook)."""
    lines = (
        OrderLine.objects.filter(product=product, order__store_id=product.store_id)
        .exclude(order__fulfilment_status=Order.FulfilmentStatus.DRAFT)
        .select_related("order")
        .order_by("-order__created_at")[:limit]
    )
    return [
        {
            "order_id": line.order_id,
            "order_number": line.order.number,
            "quantity": line.quantity,
            "line_total": line.line_total,
            "fulfilment_status": line.order.fulfilment_status,
            "created_at": line.order.created_at,
        }
        for line in lines
    ]

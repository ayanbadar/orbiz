"""
Tool catalog for Orbiz AI: Responses-API schemas plus server-side dispatch.

Each dispatch function returns (output_for_model, side_effect):
- `output_for_model` is JSON-serializable data fed back to the LLM as the
  function_call_output so it can phrase a reply.
- `side_effect` is `None`, or `{"kind": "order_created", "order_id": ...}` /
  `{"kind": "action", "action_id": ...}` — collected by services.run_turn and
  returned to the API response. Only create_draft_order emits "order_created" —
  every other order-touching tool (checkout, invoice, cancel, transition, ...)
  returns None, since the order it touches already has its own card (or never
  had one); reusing the same signal for "touched" as "created" is what made an
  unrelated action re-trigger a draft-order card at the wrong place in the chat.

Mutating tools are split into two tiers (see the plan): auto-execute tools call
the real service function directly and write an assistant-attributed OrderEvent
note; propose-only tools create a pending AssistantAction and touch nothing else.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from typing import Any, Callable

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, F, Q
from django.utils import timezone

from apps.assistant.models import AssistantAction, AssistantCreatedOrder
from apps.common.exceptions import ApplicationError
from apps.customers import services as customer_services
from apps.customers.models import Customer
from apps.orders import services as orders_services
from apps.orders.models import Order, OrderEvent
from apps.payments import emails as payment_emails
from apps.payments import services as payments_services
from apps.products import channel3
from apps.products import services as products_services
from apps.products.models import Product

logger = logging.getLogger(__name__)

DispatchResult = tuple[dict[str, Any], dict[str, Any] | None]


def _error_message(exc: Exception) -> str:
    if isinstance(exc, ApplicationError):
        return exc.message
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            return "; ".join(f"{k}: {', '.join(v)}" for k, v in exc.message_dict.items())
        return "; ".join(exc.messages)
    return str(exc)


def _order_or_none(*, store, order_id: int | None = None, order_number: str = "") -> Order | None:
    qs = Order.objects.filter(store=store)
    if order_id:
        return qs.filter(pk=order_id).select_related("customer").first()
    if order_number:
        return qs.filter(number=order_number).select_related("customer").first()
    return None


def _record_assistant_note(*, order: Order, user, message: str) -> None:
    OrderEvent.objects.create(
        order=order,
        event_type=OrderEvent.EventType.NOTE,
        origin=OrderEvent.Origin.ASSISTANT,
        actor=user if getattr(user, "pk", None) else None,
        message=message,
    )


def _resolve_order_lines(
    *, store, lines: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]] | None, dict[str, Any] | None]:
    """
    Each raw line names a product by `product` (its name or SKU) — resolved fresh via the same
    search every other mutation tool uses (_resolve_product_for_mutation), never a trusted id.
    Returns (resolved, problem); exactly one is set. `sku` is still accepted as a fallback key
    so an older/model-habit call shape still resolves correctly, not just "product".
    """
    resolved: list[dict[str, Any]] = []
    for raw in lines or []:
        query = raw.get("product") or raw.get("sku") or ""
        product, problem = _resolve_product_for_mutation(store=store, query=query)
        if problem:
            return None, problem
        resolved.append({"product_id": product.id, "quantity": raw.get("quantity")})
    return resolved, None


def _product_choices(products: list[Product]) -> list[dict[str, Any]]:
    return [{"name": p.name, "sku": p.sku, "stock_quantity": p.stock_quantity} for p in products]


def _resolve_product_for_mutation(
    *, store, query: str
) -> tuple[Product | None, dict[str, Any] | None]:
    """
    Find the product a stock/catalog change targets by searching its name or SKU, fresh, on
    every call. Never takes an id: a model-remembered id is exactly what kept resolving to the
    wrong product across multi-turn exchanges. Returns (product, problem); exactly one is set.
    """
    query = (query or "").strip()
    if not query:
        return None, {"error": "Say which product (its name or SKU) — nothing was changed."}

    products = Product.objects.filter(store=store)
    exact = list(products.filter(Q(name__iexact=query) | Q(sku__iexact=query))[:10])
    if len(exact) == 1:
        return exact[0], None

    candidates = exact or list(
        products.filter(Q(name__icontains=query) | Q(sku__icontains=query)).order_by("name")[:10]
    )
    if len(candidates) == 1:
        return candidates[0], None
    if not candidates:
        return None, {
            "error": f"No product matches '{query}'. Nothing was changed — check the name with find_products."
        }
    return None, {
        "multiple_matches": _product_choices(candidates),
        "note": (
            f"'{query}' matches {len(candidates)} products, so nothing was changed. Ask the "
            "seller which one, then retry with that product's exact SKU."
        ),
    }


# A typo'd name and its original differ mainly in word order or a letter or two, so compare
# word-sorted strings rather than raw ones — "orbiz test email" vs "orbiz email test" is a
# likely-same-customer near-miss, but raw SequenceMatcher barely registers it as similar.
FUZZY_NAME_MATCH_THRESHOLD = 0.8


def _normalized_name(value: str) -> str:
    return " ".join(sorted((value or "").strip().lower().split()))


def _name_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalized_name(a), _normalized_name(b)).ratio()


def _resolve_customer(
    *,
    store,
    customer_id: int | None = None,
    name: str = "",
    email: str = "",
    phone: str = "",
    notes: str = "",
    confirmed_new: bool = False,
) -> tuple[Customer | None, bool, dict[str, Any] | None]:
    """
    Returns (customer, was_existing, ambiguity). Exactly one of `customer`/`ambiguity` is set.

    `ambiguity` means: don't create or use anyone yet — a tool caller must surface its `note`
    to the seller and wait for an answer before calling again (with the matched id, or with
    confirmed_new=True once the seller confirms it's genuinely a new customer).
    """
    if customer_id:
        existing = Customer.objects.filter(store=store, pk=customer_id).first()
        if existing is not None:
            return existing, True, None

    name = (name or "").strip()
    email = (email or "").strip()
    phone = (phone or "").strip()
    if not name:
        return None, False, None

    existing = None
    if email:
        existing = Customer.objects.filter(store=store, email__iexact=email).first()
    if existing is None and phone:
        existing = Customer.objects.filter(store=store, phone=phone).first()
    if existing is None:
        # Unlike email/phone, a name is not unique — more than one customer can share it, and
        # silently picking .first() risks attaching the order to the wrong person.
        name_matches = list(
            Customer.objects.filter(store=store, name__iexact=name).only(
                "id", "name", "email", "phone"
            )[:5]
        )
        if len(name_matches) == 1:
            existing = name_matches[0]
        elif len(name_matches) > 1:
            return (
                None,
                False,
                {
                    "multiple_matches": [
                        {"id": c.id, "name": c.name, "email": c.email, "phone": c.phone}
                        for c in name_matches
                    ],
                    "typed_name": name,
                    "note": (
                        f"There are {len(name_matches)} existing customers named '{name}'. Stop "
                        "and ask the seller which one (share each match's email/phone so they "
                        "can tell them apart), then retry with that customer's id."
                    ),
                },
            )
    if existing is not None:
        return existing, True, None

    if not confirmed_new:
        best: Customer | None = None
        best_score = 0.0
        for candidate in Customer.objects.filter(store=store).only("id", "name", "email", "phone"):
            score = _name_similarity(name, candidate.name)
            if score > best_score:
                best, best_score = candidate, score
        if best is not None and best_score >= FUZZY_NAME_MATCH_THRESHOLD:
            return (
                None,
                False,
                {
                    "possible_match": {
                        "id": best.id,
                        "name": best.name,
                        "email": best.email,
                        "phone": best.phone,
                    },
                    "typed_name": name,
                    "note": (
                        f"'{name}' doesn't exactly match any existing customer, but it's close "
                        f"to '{best.name}'. Stop and ask the seller: did they mean {best.name}, "
                        f"or should a new customer named '{name}' be created? Do not create or "
                        "use either one until they answer."
                    ),
                },
            )

    customer = customer_services.create_customer(
        store=store, name=name, email=email, phone=phone, notes=notes
    )
    return customer, False, None


# --- Auto-execute, read-only --------------------------------------------------------


# Store-wide lists are capped. Each says how many exist and whether it was cut off — without
# that, the model read 25 rows as the whole store and gave a customer's count from a partial list.
STORE_LIST_LIMIT = 25
CUSTOMER_ORDERS_LIMIT = 100
_UNSETTLED_PAYMENT_STATUSES = (Order.PaymentStatus.UNPAID, Order.PaymentStatus.PENDING)


def _list_meta(*, shown: int, total: int, what: str) -> dict[str, Any]:
    meta: dict[str, Any] = {"total_count": total, "truncated": total > shown}
    if total > shown:
        meta["note"] = (
            f"Only {shown} of {total} {what} are listed — this is NOT the full list. Never count "
            "or summarise from it as if it were complete. For one customer's orders call "
            "list_customer_orders."
        )
    return meta


def _tool_list_unpaid_orders(
    *, store, user, conversation, min_days_unpaid: int = 0, **_: Any
) -> DispatchResult:
    cutoff = timezone.now() - timedelta(days=max(min_days_unpaid, 0))
    matching = Order.objects.filter(
        store=store,
        payment_status__in=_UNSETTLED_PAYMENT_STATUSES,
        created_at__lte=cutoff,
    )
    total = matching.count()
    qs = matching.select_related("customer").order_by("created_at")[:STORE_LIST_LIMIT]
    now = timezone.now()
    orders = [
        {
            "order_id": o.id,
            "order_number": o.number,
            "customer_id": o.customer_id,
            "customer_name": o.customer.name,
            "total": str(o.total),
            "currency": o.currency,
            "payment_status": o.payment_status,
            "fulfilment_status": o.fulfilment_status,
            "days_old": (now - o.created_at).days,
        }
        for o in qs
    ]
    return {
        "orders": orders,
        **_list_meta(shown=len(orders), total=total, what="unpaid/pending orders"),
    }, None


def _tool_order_status_summary(*, store, user, conversation, **_: Any) -> DispatchResult:
    # order_by() clears the model's default `-created_at` ordering — left in place it joins
    # the GROUP BY and silently turns this into one row per order instead of per status.
    fulfilment_counts = dict(
        Order.objects.filter(store=store)
        .order_by()
        .values_list("fulfilment_status")
        .annotate(count=Count("id"))
    )
    payment_counts = dict(
        Order.objects.filter(store=store)
        .order_by()
        .values_list("payment_status")
        .annotate(count=Count("id"))
    )
    return {
        "total_orders": sum(fulfilment_counts.values()),
        "by_fulfilment_status": fulfilment_counts,
        "by_payment_status": payment_counts,
    }, None


def _tool_list_low_stock_products(*, store, user, conversation, **_: Any) -> DispatchResult:
    qs = Product.objects.filter(
        store=store, is_active=True, stock_quantity__lte=F("low_stock_threshold")
    ).order_by("stock_quantity")[:25]
    products = [
        {
            "name": p.name,
            "sku": p.sku,
            "stock_quantity": p.stock_quantity,
            "low_stock_threshold": p.low_stock_threshold,
        }
        for p in qs
    ]
    return {"products": products}, None


def _tool_get_order(*, store, user, conversation, order_number: str, **_: Any) -> DispatchResult:
    order = _order_or_none(store=store, order_number=order_number)
    if order is None:
        return {"error": f"Order {order_number} was not found."}, None
    return {
        "order_id": order.id,
        "order_number": order.number,
        "customer_name": order.customer.name,
        "fulfilment_status": order.fulfilment_status,
        "payment_status": order.payment_status,
        "total": str(order.total),
        "currency": order.currency,
        "delivery_notes": order.delivery_notes,
        "internal_notes": order.internal_notes,
        "source_message": order.source_message,
        "lines": [
            {"product_name": line.product_name, "sku": line.sku, "quantity": line.quantity}
            for line in order.lines.all()
        ],
    }, None


def _tool_list_recent_orders(*, store, user, conversation, limit: int = 10, **_: Any) -> DispatchResult:
    capped = min(max(limit, 1), STORE_LIST_LIMIT)
    all_orders = Order.objects.filter(store=store)
    total = all_orders.count()
    qs = all_orders.select_related("customer").order_by("-created_at")[:capped]
    orders = [
        {
            "order_id": o.id,
            "order_number": o.number,
            "customer_id": o.customer_id,
            "customer_name": o.customer.name,
            "fulfilment_status": o.fulfilment_status,
            "payment_status": o.payment_status,
            "total": str(o.total),
            "currency": o.currency,
        }
        for o in qs
    ]
    return {
        "orders": orders,
        **_list_meta(shown=len(orders), total=total, what="orders in the store"),
    }, None


def _tool_find_customers(*, store, user, conversation, query: str, **_: Any) -> DispatchResult:
    qs = Customer.objects.filter(store=store).filter(
        Q(name__icontains=query) | Q(email__icontains=query) | Q(phone__icontains=query)
    )[:10]
    customers = [
        {"id": c.id, "name": c.name, "email": c.email, "phone": c.phone, "notes": c.notes}
        for c in qs
    ]
    return {"customers": customers}, None


def _find_existing_customer(
    *, store, customer_id: int | None, query: str
) -> tuple[Customer | None, dict[str, Any] | None]:
    """
    Read-only customer lookup for questions about a customer — unlike _resolve_customer it never
    creates anyone. Returns (customer, problem); exactly one is set. Exact email → phone → name
    first, then a partial match; more than one hit is handed back for the seller to pick.
    """
    customers = Customer.objects.filter(store=store)
    if customer_id:
        found = customers.filter(pk=customer_id).first()
        if found is not None:
            return found, None

    query = (query or "").strip()
    if not query:
        return None, {"error": "Say which customer — their name, email, or phone."}

    matches: list[Customer] = []
    for exact in (Q(email__iexact=query), Q(phone=query), Q(name__iexact=query)):
        matches = list(customers.filter(exact)[:5])
        if matches:
            break
    if not matches:
        matches = list(
            customers.filter(
                Q(name__icontains=query) | Q(email__icontains=query) | Q(phone__icontains=query)
            )[:5]
        )

    if len(matches) == 1:
        return matches[0], None
    if not matches:
        return None, {"error": f"No customer matches '{query}'."}
    return None, {
        "multiple_matches": [
            {"id": c.id, "name": c.name, "email": c.email, "phone": c.phone} for c in matches
        ],
        "note": (
            f"More than one customer matches '{query}'. Stop and ask the seller which one "
            "(share each match's email/phone so they can tell them apart), then call again "
            "with that customer's id."
        ),
    }


def _open_payment_request(order: Order) -> str:
    if order.payment_status not in _UNSETTLED_PAYMENT_STATUSES:
        return "none"
    kind = payments_services.payment_request_summary(order=order)["kind"]
    return {"invoice": "invoice_open", "checkout": "pay_now_link_open"}.get(kind, "none")


def _tool_list_customer_orders(
    *, store, user, conversation, customer_id: int | None = None, customer: str = "", **_: Any
) -> DispatchResult:
    found, problem = _find_existing_customer(store=store, customer_id=customer_id, query=customer)
    if problem is not None:
        return problem, None

    orders_qs = Order.objects.filter(store=store, customer=found)
    # order_by() first: the model's default ordering would otherwise join the GROUP BY.
    by_payment_status = dict(
        orders_qs.order_by().values_list("payment_status").annotate(count=Count("id"))
    )
    total = sum(by_payment_status.values())
    orders = [
        {
            "order_id": o.id,
            "order_number": o.number,
            "created": o.created_at.date().isoformat(),
            "total": str(o.total),
            "currency": o.currency,
            "payment_status": o.payment_status,
            "fulfilment_status": o.fulfilment_status,
            "open_payment_request": _open_payment_request(o),
        }
        for o in orders_qs.order_by("-created_at")[:CUSTOMER_ORDERS_LIMIT]
    ]
    return {
        "customer": {
            "id": found.id,
            "name": found.name,
            "email": found.email,
            "phone": found.phone,
        },
        "total_orders": total,
        "by_payment_status": by_payment_status,
        "orders": orders,
        **_list_meta(shown=len(orders), total=total, what="orders for this customer"),
    }, None


def _tool_find_products(*, store, user, conversation, query: str, **_: Any) -> DispatchResult:
    qs = Product.objects.filter(store=store).filter(
        Q(name__icontains=query) | Q(sku__icontains=query)
    ).order_by("name")[:15]
    products = [
        {
            "name": p.name,
            "sku": p.sku,
            "price": str(p.price),
            "currency": p.currency,
            "stock_quantity": p.stock_quantity,
            "is_active": p.is_active,
        }
        for p in qs
    ]
    return {"products": products}, None


def _tool_search_channel3_products(*, store, user, conversation, query: str, **_: Any) -> DispatchResult:
    try:
        result = channel3.search_products(query=query, limit=5)
    except channel3.Channel3Error as exc:
        return {"error": str(exc)}, None
    return result, None


# --- Auto-execute, mutation (no confirm step — none of these move money) ------------


def _tool_create_draft_order(
    *,
    store,
    user,
    conversation,
    customer: dict[str, Any],
    lines: list[dict[str, Any]],
    delivery_notes: str = "",
    internal_notes: str = "",
    source_message: str = "",
    **_: Any,
) -> DispatchResult:
    customer = customer or {}
    customer_obj, _was_existing, ambiguity = _resolve_customer(
        store=store,
        customer_id=customer.get("id"),
        name=customer.get("name", ""),
        email=customer.get("email", ""),
        phone=customer.get("phone", ""),
        confirmed_new=bool(customer.get("confirmed_new")),
    )
    if ambiguity:
        return ambiguity, None
    if customer_obj is None:
        return {"error": "Need at least the customer's name to create an order."}, None

    resolved_lines, problem = _resolve_order_lines(store=store, lines=lines)
    if problem:
        return problem, None

    try:
        order = orders_services.create_draft(
            store=store,
            user=user,
            customer=customer_obj,
            lines=resolved_lines,
            delivery_notes=delivery_notes,
            internal_notes=internal_notes,
            source_message=source_message,
        )
    except (DjangoValidationError, ApplicationError) as exc:
        return {"error": _error_message(exc)}, None

    _record_assistant_note(order=order, user=user, message="Draft order created via Orbiz AI.")
    if conversation is not None:
        AssistantCreatedOrder.objects.create(conversation=conversation, order=order)
    return (
        {"order_number": order.number, "total": str(order.total), "currency": order.currency},
        {"kind": "order_created", "order_id": order.id},
    )


def _tool_update_draft_order(
    *,
    store,
    user,
    conversation,
    order_id: int,
    customer_id: int | None = None,
    lines: list[dict[str, Any]] | None = None,
    delivery_notes: str | None = None,
    internal_notes: str | None = None,
    source_message: str | None = None,
    **_: Any,
) -> DispatchResult:
    order = _order_or_none(store=store, order_id=order_id)
    if order is None:
        return {"error": "Order not found."}, None

    customer_obj = None
    if customer_id is not None:
        customer_obj = Customer.objects.filter(store=store, pk=customer_id).first()
        if customer_obj is None:
            return {"error": "Customer not found."}, None

    resolved_lines = None
    if lines is not None:
        resolved_lines, problem = _resolve_order_lines(store=store, lines=lines)
        if problem:
            return problem, None

    try:
        order = orders_services.update_draft(
            order=order,
            user=user,
            customer=customer_obj,
            lines=resolved_lines,
            delivery_notes=delivery_notes,
            internal_notes=internal_notes,
            source_message=source_message,
        )
    except (DjangoValidationError, ApplicationError) as exc:
        return {"error": _error_message(exc)}, None

    _record_assistant_note(order=order, user=user, message="Draft order updated via Orbiz AI.")
    return {"order_number": order.number, "total": str(order.total), "currency": order.currency}, None


def _tool_cancel_order(*, store, user, conversation, order_id: int, **_: Any) -> DispatchResult:
    order = _order_or_none(store=store, order_id=order_id)
    if order is None:
        return {"error": "Order not found."}, None
    try:
        order = orders_services.cancel_order(order=order, user=user)
    except (DjangoValidationError, ApplicationError) as exc:
        return {"error": _error_message(exc)}, None
    _record_assistant_note(order=order, user=user, message="Order cancelled via Orbiz AI.")
    return {"order_number": order.number, "fulfilment_status": order.fulfilment_status}, None


def _tool_mark_order_paid(*, store, user, conversation, order_id: int, **_: Any) -> DispatchResult:
    order = _order_or_none(store=store, order_id=order_id)
    if order is None:
        return {"error": "Order not found."}, None
    try:
        order = orders_services.mark_order_paid(order=order, user=user)
    except ApplicationError as exc:
        return {"error": exc.message}, None
    _record_assistant_note(order=order, user=user, message="Payment marked paid via Orbiz AI.")
    return {"order_number": order.number, "payment_status": order.payment_status}, None


def _tool_transition_order_status(
    *,
    store,
    user,
    conversation,
    order_id: int,
    fulfilment_status: str,
    allow_unpaid: bool = False,
    **_: Any,
) -> DispatchResult:
    order = _order_or_none(store=store, order_id=order_id)
    if order is None:
        return {"error": "Order not found."}, None
    try:
        order = orders_services.transition_fulfilment(
            order=order, user=user, fulfilment_status=fulfilment_status, allow_unpaid=allow_unpaid
        )
    except ApplicationError as exc:
        return {"error": exc.message}, None
    _record_assistant_note(
        order=order, user=user, message=f"Order moved to {fulfilment_status} via Orbiz AI."
    )
    return {"order_number": order.number, "fulfilment_status": order.fulfilment_status}, None


def _tool_abandon_order_payment(*, store, user, conversation, order_id: int, **_: Any) -> DispatchResult:
    order = _order_or_none(store=store, order_id=order_id)
    if order is None:
        return {"error": "Order not found."}, None
    try:
        order = orders_services.abandon_payment(order=order, user=user)
    except ApplicationError as exc:
        return {"error": exc.message}, None
    _record_assistant_note(order=order, user=user, message="Payment attempt abandoned via Orbiz AI.")
    return {"order_number": order.number, "payment_status": order.payment_status}, None


# --- Auto-execute, mutation: catalog (no money, no order involved) -----------------


def _tool_adjust_product_stock(
    *,
    store,
    user,
    conversation,
    delta: int,
    reason: str,
    product: str = "",
    **_: Any,
) -> DispatchResult:
    product, problem = _resolve_product_for_mutation(store=store, query=product)
    if problem:
        return problem, None
    try:
        adjustment = products_services.adjust_stock(
            product=product, delta=delta, reason=reason, user=user
        )
    except DjangoValidationError as exc:
        return {"error": _error_message(exc)}, None
    return {
        "product_name": product.name,
        "sku": product.sku,
        "stock_quantity_before": adjustment.quantity_before,
        "stock_quantity_after": adjustment.quantity_after,
    }, None


def _tool_create_product(
    *,
    store,
    user,
    conversation,
    name: str,
    sku: str,
    price: str,
    description: str = "",
    stock_quantity: int = 0,
    low_stock_threshold: int = 5,
    is_active: bool = True,
    **_: Any,
) -> DispatchResult:
    name = (name or "").strip()
    sku = (sku or "").strip().upper()
    if not name:
        return {"error": "A product name is required."}, None
    if not sku:
        return {"error": "A SKU is required."}, None
    try:
        price_value = Decimal(str(price))
    except InvalidOperation:
        return {"error": f"Invalid price: {price}"}, None
    try:
        product = products_services.create_product(
            store=store,
            name=name,
            sku=sku,
            description=description,
            price=price_value,
            stock_quantity=max(stock_quantity, 0),
            low_stock_threshold=max(low_stock_threshold, 0),
            is_active=is_active,
        )
    except (DjangoValidationError, ApplicationError) as exc:
        return {"error": _error_message(exc)}, None
    return {"product_id": product.id, "name": product.name, "sku": product.sku}, None


def _tool_update_product(
    *,
    store,
    user,
    conversation,
    product: str = "",
    name: str | None = None,
    new_sku: str | None = None,
    price: str | None = None,
    description: str | None = None,
    low_stock_threshold: int | None = None,
    is_active: bool | None = None,
    **_: Any,
) -> DispatchResult:
    product, problem = _resolve_product_for_mutation(store=store, query=product)
    if problem:
        return problem, None

    fields: dict[str, Any] = {}
    if name is not None:
        fields["name"] = name.strip()
    if new_sku is not None:
        fields["sku"] = new_sku.strip().upper()
    if price is not None:
        try:
            fields["price"] = Decimal(str(price))
        except InvalidOperation:
            return {"error": f"Invalid price: {price}"}, None
    if description is not None:
        fields["description"] = description
    if low_stock_threshold is not None:
        fields["low_stock_threshold"] = low_stock_threshold
    if is_active is not None:
        fields["is_active"] = is_active

    if not fields:
        return {"error": "Nothing to update."}, None

    try:
        product = products_services.update_product(product=product, **fields)
    except (DjangoValidationError, ApplicationError) as exc:
        return {"error": _error_message(exc)}, None
    return {
        "product_id": product.id,
        "name": product.name,
        "sku": product.sku,
        "price": str(product.price),
        "is_active": product.is_active,
    }, None


def _tool_add_customer(
    *,
    store,
    user,
    conversation,
    name: str,
    email: str = "",
    phone: str = "",
    notes: str = "",
    confirmed_new: bool = False,
    **_: Any,
) -> DispatchResult:
    name = (name or "").strip()
    if not name:
        return {"error": "A name is required to add a customer."}, None
    customer, was_existing, ambiguity = _resolve_customer(
        store=store, name=name, email=email, phone=phone, notes=notes, confirmed_new=confirmed_new
    )
    if ambiguity:
        return ambiguity, None
    if was_existing:
        return {
            "customer_id": customer.id,
            "name": customer.name,
            "note": "A matching customer already existed — using that record.",
        }, None
    return {"customer_id": customer.id, "name": customer.name}, None


def _tool_update_customer_notes(
    *, store, user, conversation, customer_id: int, notes: str, **_: Any
) -> DispatchResult:
    customer = Customer.objects.filter(store=store, pk=customer_id).first()
    if customer is None:
        return {"error": "Customer not found."}, None
    customer_services.update_customer(customer=customer, notes=notes)
    return {"customer_id": customer.id, "notes": customer.notes}, None


def _tool_create_checkout(*, store, user, conversation, order_id: int, **_: Any) -> DispatchResult:
    order = _order_or_none(store=store, order_id=order_id)
    if order is None:
        return {"error": "Order not found."}, None
    try:
        checkout = payments_services.create_checkout(order_id=order.id, store=store, user=user)
    except ApplicationError as exc:
        return {"error": exc.message}, None
    _record_assistant_note(order=order, user=user, message="PayPal checkout created via Orbiz AI.")
    return {"order_number": order.number, "approve_url": checkout.approve_url}, None


def _tool_send_invoice(
    *, store, user, conversation, order_id: int, recipient_email: str = "", **_: Any
) -> DispatchResult:
    order = _order_or_none(store=store, order_id=order_id)
    if order is None:
        return {"error": "Order not found."}, None
    email = recipient_email or order.customer.email
    try:
        invoice = payments_services.send_invoice_for_order(
            order_id=order.id, store=store, user=user, recipient_email=email
        )
    except ApplicationError as exc:
        return {"error": exc.message}, None
    _record_assistant_note(order=order, user=user, message="Invoice sent via Orbiz AI.")
    return {"order_number": order.number, "invoice_number": invoice.invoice_number}, None


def _tool_email_payment_link(
    *, store, user, conversation, order_id: int, recipient_email: str = "", **_: Any
) -> DispatchResult:
    """Same as the order page's "Email link" button, creating the pay-now link first if needed."""
    order = _order_or_none(store=store, order_id=order_id)
    if order is None:
        return {"error": "Order not found."}, None
    try:
        if payments_services.payment_request_summary(order=order)["kind"] == "none":
            payments_services.create_checkout(order_id=order.id, store=store, user=user)
        log = payments_services.email_payment_link(
            order_id=order.id,
            store=store,
            user=user,
            recipient_email=recipient_email,
            kind=payment_emails.REQUEST,
        )
    except ApplicationError as exc:
        return {"error": exc.message}, None
    _record_assistant_note(
        order=order, user=user, message=f"Payment link emailed to {log.recipient} via Orbiz AI."
    )
    sent = payments_services.payment_request_summary(order=order)["kind"]
    return {"order_number": order.number, "emailed_to": log.recipient, "link_type": sent}, None


def _tool_send_reminder(*, store, user, conversation, order_id: int, **_: Any) -> DispatchResult:
    order = _order_or_none(store=store, order_id=order_id)
    if order is None:
        return {"error": "Order not found."}, None
    try:
        payments_services.email_payment_link(
            order_id=order.id, store=store, user=user, kind=payment_emails.REMINDER
        )
    except ApplicationError as exc:
        return {"error": exc.message}, None
    _record_assistant_note(order=order, user=user, message="Payment reminder sent via Orbiz AI.")
    return {"order_number": order.number, "note": "Reminder sent."}, None


def _tool_cancel_invoice(*, store, user, conversation, order_id: int, **_: Any) -> DispatchResult:
    order = _order_or_none(store=store, order_id=order_id)
    if order is None:
        return {"error": "Order not found."}, None
    try:
        payments_services.cancel_invoice_for_order(order_id=order.id, store=store, user=user)
    except ApplicationError as exc:
        return {"error": exc.message}, None
    _record_assistant_note(order=order, user=user, message="Invoice cancelled via Orbiz AI.")
    return {"order_number": order.number, "note": "Invoice cancelled."}, None


# --- Propose -> confirm (money settlement, or missing required fields) --------------


def _tool_propose_refund(
    *, store, user, conversation, order_id: int, amount: str | None = None, **_: Any
) -> DispatchResult:
    order = _order_or_none(store=store, order_id=order_id)
    if order is None:
        return {"error": "Order not found."}, None
    action = AssistantAction.objects.create(
        store=store,
        conversation=conversation,
        order=order,
        action_type=AssistantAction.ActionType.REFUND,
        payload={"amount": amount},
        created_by=user,
    )
    return (
        {"action_id": action.id, "order_number": order.number, "note": "Waiting for the seller to confirm."},
        {"kind": "action", "action_id": action.id},
    )


def _tool_propose_capture_checkout(*, store, user, conversation, order_id: int, **_: Any) -> DispatchResult:
    order = _order_or_none(store=store, order_id=order_id)
    if order is None:
        return {"error": "Order not found."}, None
    action = AssistantAction.objects.create(
        store=store,
        conversation=conversation,
        order=order,
        action_type=AssistantAction.ActionType.CAPTURE,
        payload={},
        created_by=user,
    )
    return (
        {"action_id": action.id, "order_number": order.number, "note": "Waiting for the seller to confirm."},
        {"kind": "action", "action_id": action.id},
    )


def _tool_propose_import_product(
    *,
    store,
    user,
    conversation,
    channel3_product_id: str,
    sku: str,
    price: str,
    stock_quantity: int,
    low_stock_threshold: int = 5,
    **_: Any,
) -> DispatchResult:
    try:
        payload = channel3.retrieve_product(channel3_product_id)
    except channel3.Channel3Error as exc:
        return {"error": str(exc)}, None
    action = AssistantAction.objects.create(
        store=store,
        conversation=conversation,
        order=None,
        action_type=AssistantAction.ActionType.IMPORT_PRODUCT,
        payload={
            "channel3_product_id": channel3_product_id,
            "sku": sku,
            "price": price,
            "stock_quantity": stock_quantity,
            "low_stock_threshold": low_stock_threshold,
            "channel3_payload": payload,
        },
        created_by=user,
    )
    return (
        {"action_id": action.id, "title": payload.get("title"), "note": "Waiting for the seller to confirm."},
        {"kind": "action", "action_id": action.id},
    )


_DISPATCH: dict[str, Callable[..., DispatchResult]] = {
    "list_unpaid_orders": _tool_list_unpaid_orders,
    "order_status_summary": _tool_order_status_summary,
    "list_low_stock_products": _tool_list_low_stock_products,
    "get_order": _tool_get_order,
    "list_recent_orders": _tool_list_recent_orders,
    "find_customers": _tool_find_customers,
    "list_customer_orders": _tool_list_customer_orders,
    "find_products": _tool_find_products,
    "search_channel3_products": _tool_search_channel3_products,
    "create_draft_order": _tool_create_draft_order,
    "update_draft_order": _tool_update_draft_order,
    "cancel_order": _tool_cancel_order,
    "mark_order_paid": _tool_mark_order_paid,
    "transition_order_status": _tool_transition_order_status,
    "abandon_order_payment": _tool_abandon_order_payment,
    "adjust_product_stock": _tool_adjust_product_stock,
    "create_product": _tool_create_product,
    "update_product": _tool_update_product,
    "add_customer": _tool_add_customer,
    "update_customer_notes": _tool_update_customer_notes,
    "create_checkout": _tool_create_checkout,
    "send_invoice": _tool_send_invoice,
    "email_payment_link": _tool_email_payment_link,
    "send_reminder": _tool_send_reminder,
    "cancel_invoice": _tool_cancel_invoice,
    "propose_refund": _tool_propose_refund,
    "propose_capture_checkout": _tool_propose_capture_checkout,
    "propose_import_product": _tool_propose_import_product,
}


def dispatch(name: str, *, store, user, conversation, arguments: dict[str, Any]) -> DispatchResult:
    func = _DISPATCH.get(name)
    if func is None:
        return {"error": f"Unknown tool: {name}"}, None
    try:
        return func(store=store, user=user, conversation=conversation, **(arguments or {}))
    except Exception as exc:  # noqa: BLE001 — a bad tool call must surface in chat, never 500 the turn
        logger.exception("Orbiz AI tool %s failed", name)
        return {"error": _error_message(exc) if isinstance(exc, ApplicationError) else "Something went wrong running that action."}, None


# --- Responses API tool schemas -------------------------------------------------------

_ORDER_LINE_ITEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "product": {
            "type": "string",
            "description": (
                "The product's name or SKU, e.g. \"Mag Tote Bag\" or \"MAG-TOTE-BAG\" — looked "
                "up fresh on every call, by name or SKU search. Never invent one: if you're not "
                "sure it's in the catalog, call find_products first and use what it returns."
            ),
        },
        "quantity": {"type": "integer"},
    },
    "required": ["product", "quantity"],
}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "list_unpaid_orders",
        "description": (
            "List the whole store's orders that are unpaid or pending payment, oldest first, "
            "capped at 25 — check `truncated`. Not for one customer's orders: use "
            "list_customer_orders for that."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "min_days_unpaid": {
                    "type": "integer",
                    "description": "Only orders unpaid at least this many days. 0 means all unpaid orders.",
                }
            },
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "order_status_summary",
        "description": (
            "Get exact order counts grouped by fulfilment status and by payment status. "
            "Use this for any question about how many orders exist, in total or by status "
            "— never estimate or recall counts from earlier in the conversation."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "type": "function",
        "name": "list_low_stock_products",
        "description": "List active products at or below their low-stock threshold.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "type": "function",
        "name": "get_order",
        "description": "Look up one order by its order number, including the original customer message if any.",
        "parameters": {
            "type": "object",
            "properties": {"order_number": {"type": "string"}},
            "required": ["order_number"],
        },
    },
    {
        "type": "function",
        "name": "list_recent_orders",
        "description": (
            "List the store's most recently created orders (max 25), across all customers. "
            "Not for one customer's orders: use list_customer_orders for that."
        ),
        "parameters": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "description": "Max 25."}},
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "find_customers",
        "description": "Search customers by name, email, or phone.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "type": "function",
        "name": "list_customer_orders",
        "description": (
            "Every order for ONE customer, newest first, with exact counts by payment status and, "
            "for each unpaid/pending order, whether a PayPal invoice or pay-now link is open. Use "
            "this for any question about a specific customer's orders, payments, or invoices — "
            "never filter list_unpaid_orders or list_recent_orders by name instead (they are "
            "store-wide and capped, and two customers can share a name). Never creates a customer."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "integer",
                    "description": (
                        "The customer's id, when known — e.g. after the seller picked one of "
                        "several matches."
                    ),
                },
                "customer": {
                    "type": "string",
                    "description": "The customer's name, email, or phone, as the seller said it.",
                },
            },
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "find_products",
        "description": (
            "Search the seller's OWN product catalog (already added or imported) by name or "
            "SKU. Always try this first for any question about whether the seller has, sells, "
            "or stocks an item — before ever considering Channel3."
        ),
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "type": "function",
        "name": "search_channel3_products",
        "description": (
            "Search Channel3's external catalog for items that could be imported as NEW "
            "products. Only call this when the seller is explicitly looking for something new "
            "to add, or after find_products confirms the item isn't already in their catalog — "
            "never as a way to answer 'do I have X' or 'do I sell X'."
        ),
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "type": "function",
        "name": "create_draft_order",
        "description": (
            "Create a Draft order from a customer's request. This is safe to call immediately — "
            "a Draft order deducts no stock and is fully editable by the seller before it is "
            "confirmed. Always pass the original customer message as source_message."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "customer": {
                    "type": "object",
                    "description": (
                        "Either {\"id\": <existing customer id>} or {\"name\", \"email\"?, "
                        "\"phone\"?}. An existing customer is matched automatically — don't ask "
                        "the seller up front whether one exists, just pass the name. If it's "
                        "close to but not an exact match, the call returns a possible_match "
                        "instead of creating anyone; if the exact name matches more than one "
                        "customer, it returns multiple_matches. Either way, ask the seller "
                        "before retrying."
                    ),
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                        "phone": {"type": "string"},
                        "confirmed_new": {
                            "type": "boolean",
                            "description": (
                                "Set true only after the seller has explicitly confirmed this "
                                "is a brand-new customer (e.g. you asked about a near-match and "
                                "they said no), to skip the near-match check on this retry."
                            ),
                        },
                    },
                },
                "lines": {"type": "array", "items": _ORDER_LINE_ITEM_SCHEMA},
                "delivery_notes": {"type": "string"},
                "internal_notes": {"type": "string"},
                "source_message": {"type": "string", "description": "The customer's original message, verbatim."},
            },
            "required": ["customer", "lines"],
        },
    },
    {
        "type": "function",
        "name": "update_draft_order",
        "description": (
            "Edit a Draft order before it's confirmed — change its lines, reassign its "
            "customer, or update its delivery/internal notes or source message. Only works "
            "while the order is still a Draft."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "integer"},
                "customer_id": {"type": "integer", "description": "Reassign to a different existing customer."},
                "lines": {
                    "type": "array",
                    "description": "Replaces every line on the order. Omit to leave the lines unchanged.",
                    "items": _ORDER_LINE_ITEM_SCHEMA,
                },
                "delivery_notes": {"type": "string"},
                "internal_notes": {"type": "string"},
                "source_message": {"type": "string"},
            },
            "required": ["order_id"],
        },
    },
    {
        "type": "function",
        "name": "cancel_order",
        "description": (
            "Cancel an order and restore any stock that was already deducted. Does not refund "
            "a paid order's payment — propose_refund separately if the seller wants money "
            "returned."
        ),
        "parameters": {
            "type": "object",
            "properties": {"order_id": {"type": "integer"}},
            "required": ["order_id"],
        },
    },
    {
        "type": "function",
        "name": "mark_order_paid",
        "description": (
            "Manually record an order's payment as paid — for cash-on-delivery or another "
            "offline payment the seller is telling you about, not a real PayPal capture."
        ),
        "parameters": {
            "type": "object",
            "properties": {"order_id": {"type": "integer"}},
            "required": ["order_id"],
        },
    },
    {
        "type": "function",
        "name": "transition_order_status",
        "description": (
            "Advance an order's fulfilment status forward: to processing, shipped, or "
            "completed. Requires the order to already be paid unless allow_unpaid is set for "
            "an explicit unpaid policy like COD."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "integer"},
                "fulfilment_status": {
                    "type": "string",
                    "enum": ["processing", "shipped", "completed"],
                },
                "allow_unpaid": {
                    "type": "boolean",
                    "description": "Explicit override to advance an unpaid order (e.g. COD).",
                },
            },
            "required": ["order_id", "fulfilment_status"],
        },
    },
    {
        "type": "function",
        "name": "abandon_order_payment",
        "description": (
            "Abandon a stuck pending payment attempt on an unfulfilled order so the seller can "
            "retry checkout or cancel the order separately."
        ),
        "parameters": {
            "type": "object",
            "properties": {"order_id": {"type": "integer"}},
            "required": ["order_id"],
        },
    },
    {
        "type": "function",
        "name": "adjust_product_stock",
        "description": (
            "Change a product's stock quantity up or down — a restock, a correction, or an "
            "offline sale — and record why. The product is looked up by name or SKU on every "
            "call; if that's ambiguous, nothing changes and you get the matches back to ask about."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "product": {
                    "type": "string",
                    "description": (
                        "The product's name or SKU, e.g. \"Water Bottle 750ml\" or \"BTL-750\". "
                        "Use the words the seller used for it this turn."
                    ),
                },
                "delta": {
                    "type": "integer",
                    "description": "Positive to add stock, negative to remove. Must be non-zero.",
                },
                "reason": {"type": "string"},
            },
            "required": ["product", "delta", "reason"],
        },
    },
    {
        "type": "function",
        "name": "create_product",
        "description": (
            "Add a brand-new product straight to the catalog from fields the seller gave you "
            "directly — not from Channel3, use propose_import_product for that. Only call this "
            "once you have a name, SKU, and price; ask instead of guessing if any are missing."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "sku": {"type": "string"},
                "price": {"type": "string"},
                "description": {"type": "string"},
                "stock_quantity": {"type": "integer"},
                "low_stock_threshold": {"type": "integer"},
                "is_active": {"type": "boolean"},
            },
            "required": ["name", "sku", "price"],
        },
    },
    {
        "type": "function",
        "name": "update_product",
        "description": (
            "Edit an existing product's name, SKU, price, description, low-stock threshold, or "
            "active status. The product is looked up by name or SKU on every call. For stock "
            "quantity use adjust_product_stock instead."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "product": {
                    "type": "string",
                    "description": (
                        "The product's CURRENT name or SKU, used only to find it — not a change. "
                        "Use `name` / `new_sku` to rename it."
                    ),
                },
                "name": {"type": "string", "description": "A new name to rename the product to."},
                "new_sku": {"type": "string"},
                "price": {"type": "string"},
                "description": {"type": "string"},
                "low_stock_threshold": {"type": "integer"},
                "is_active": {"type": "boolean"},
            },
            "required": ["product"],
        },
    },
    {
        "type": "function",
        "name": "add_customer",
        "description": (
            "Add a new customer, or return the matching one if it already exists — don't ask "
            "the seller up front whether one exists, just pass the name. If it's close to but "
            "not an exact match for an existing customer, this returns a possible_match instead "
            "of creating anyone; if the exact name matches more than one customer, it returns "
            "multiple_matches. Either way, ask the seller before retrying."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"},
                "notes": {"type": "string"},
                "confirmed_new": {
                    "type": "boolean",
                    "description": (
                        "Set true only after the seller has explicitly confirmed this is a "
                        "brand-new customer, to skip the near-match check on this retry."
                    ),
                },
            },
            "required": ["name"],
        },
    },
    {
        "type": "function",
        "name": "update_customer_notes",
        "description": "Update a customer's internal notes, e.g. preferences the seller should remember next time.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "notes": {"type": "string"},
            },
            "required": ["customer_id", "notes"],
        },
    },
    {
        "type": "function",
        "name": "create_checkout",
        "description": "Create a PayPal checkout link for an order. Does not move money — the buyer still has to pay.",
        "parameters": {
            "type": "object",
            "properties": {"order_id": {"type": "integer"}},
            "required": ["order_id"],
        },
    },
    {
        "type": "function",
        "name": "send_invoice",
        "description": "Send a PayPal invoice for an order. Does not move money.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "integer"},
                "recipient_email": {
                    "type": "string",
                    "description": "Only if the seller gave an address; defaults to the customer's email.",
                },
            },
            "required": ["order_id"],
        },
    },
    {
        "type": "function",
        "name": "email_payment_link",
        "description": (
            "Email the customer the order's pay-now link (the PayPal checkout link) — what "
            "\"email her the link\", \"email the pay-now link\" or \"send the payment link to "
            "her email\" mean. Creates the link first if none is open; if a PayPal invoice is "
            "the open request, its link is emailed instead. This is NOT send_invoice."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "integer"},
                "recipient_email": {
                    "type": "string",
                    "description": "Only if the seller gave an address; defaults to the customer's email.",
                },
            },
            "required": ["order_id"],
        },
    },
    {
        "type": "function",
        "name": "send_reminder",
        "description": (
            "A follow-up nudge for a payment request the customer was ALREADY sent. Not for the "
            "first send — use email_payment_link for that. Does not move money."
        ),
        "parameters": {
            "type": "object",
            "properties": {"order_id": {"type": "integer"}},
            "required": ["order_id"],
        },
    },
    {
        "type": "function",
        "name": "cancel_invoice",
        "description": "Cancel the open PayPal invoice on an order.",
        "parameters": {
            "type": "object",
            "properties": {"order_id": {"type": "integer"}},
            "required": ["order_id"],
        },
    },
    {
        "type": "function",
        "name": "propose_refund",
        "description": (
            "Propose refunding an order. This moves real money, so it does NOT execute — it "
            "creates a proposal the seller must confirm. Leave amount empty for a full refund."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "integer"},
                "amount": {"type": "string", "description": "Optional partial-refund amount."},
            },
            "required": ["order_id"],
        },
    },
    {
        "type": "function",
        "name": "propose_capture_checkout",
        "description": (
            "Propose capturing (settling) a PayPal payment the buyer has already approved. This "
            "moves real money, so it does NOT execute — it creates a proposal the seller must confirm."
        ),
        "parameters": {
            "type": "object",
            "properties": {"order_id": {"type": "integer"}},
            "required": ["order_id"],
        },
    },
    {
        "type": "function",
        "name": "propose_import_product",
        "description": (
            "Propose importing a Channel3 catalog result as a new Orbiz product. SKU, price, and "
            "stock are required because Channel3 doesn't know Orbiz's own pricing or inventory — "
            "this always creates a proposal for the seller to review, never executes immediately."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "channel3_product_id": {"type": "string"},
                "sku": {"type": "string"},
                "price": {"type": "string"},
                "stock_quantity": {"type": "integer"},
                "low_stock_threshold": {"type": "integer"},
            },
            "required": ["channel3_product_id", "sku", "price", "stock_quantity"],
        },
    },
]

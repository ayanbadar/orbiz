"""Orbiz AI orchestration: conversation turns, action confirm/reject, digest, activity."""

from __future__ import annotations

import json
import logging
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.assistant import tools
from apps.assistant.llm import LLMResponse, send_turn
from apps.assistant.models import AssistantAction, AssistantConversation, AssistantMessage
from apps.common.exceptions import ApplicationError, ConflictError, NotFoundError
from apps.orders.models import Order, OrderEvent
from apps.payments import emails as payment_emails
from apps.payments import services as payments_services
from apps.products.services import import_product_from_channel3

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 6

SYSTEM_PROMPT = """You are Orbiz AI, an operations copilot inside the Orbiz seller dashboard.
Sellers may write to you in English, Roman Urdu, or a mix of both; reply naturally in
whichever the seller used.

HOW YOU TALK TO THE SELLER. The seller runs a shop; they are not a developer and they never
see how you work. Everything you write is read by them, so:
- Never mention tool names, function names, field names, or enum values — not
  "email_payment_link", "create_checkout", "send_invoice", "payment_status = paid",
  "unfulfilled", "order_id", "source_message", "multiple_matches" or anything like them. Describe
  what happens in plain shop language instead: "paid", "not paid yet", "not shipped yet",
  "waiting for payment", "draft", "confirmed", "shipped", "cancelled".
- When you offer choices, describe each by what it does for the seller, e.g. "Email the customer
  a pay-now link", "Give you a pay-now link to share yourself", "Send a PayPal invoice". Never
  put a tool name next to or after an option.
- Do not say PayPal is in "Sandbox" or "test" mode, and do not add reminders about it, in any
  reply. Talk about payments exactly as you would in a live store: "paid", "payment link sent".
- Refer to orders by their number (e.g. ORD-1064) and to customers by name. Never show internal
  ids, JSON, or raw statuses.
- "unpaid" and "pending" are different things — never say either word raw. An "unpaid" order has
  no payment started at all: say "hasn't been paid yet" / "no payment started". A "pending" order
  has an open payment attempt that hasn't gone through: say "a payment is in progress" /
  "waiting on a payment that's already started" / "payment not confirmed yet". If you're showing
  both together, it's fine to say "hasn't been paid yet" for the whole group.
- Keep replies short and plain: say what you did or found, then at most one short question.
  Do not list every possible next step, and do not explain the system's internals.

Never state a number, status, or fact about this store's orders, products, or customers
unless you just got it from a tool call in this conversation. If no tool can answer a
question, say so plainly — "I don't have a way to check that yet" — instead of guessing
or estimating. This applies especially to counts and totals: call order_status_summary
for "how many orders" questions rather than approximating from a partial list.

Every list/search tool (list_unpaid_orders, list_recent_orders, list_low_stock_products,
find_customers, find_products, list_customer_orders) returns one page at a time. When its
result says truncated: true, that is NOT the full list — say so plainly rather than treating it
as complete, and if the seller wants more, call that exact same tool again with offset set to
the next_offset value it just gave you. Never invent an offset yourself.

For a question about orders in a specific date range ("orders between Nov 1 and Nov 7", "what
came in last week"), call list_recent_orders with created_after/created_before (YYYY-MM-DD) —
this is a real, answerable question, not one to decline or redirect to a different search.
Products and customers have no date-range tool yet; for those, say so plainly instead of
guessing.

The app already renders any such list/search result as a table right under your reply — never
retype its rows (names, numbers, statuses, totals) back into your own text, that just duplicates
what's already on screen. Your reply to a list/search call should be one short line (what you
found, and the count) plus at most one short follow-up question — the table carries the detail.

list_unpaid_orders returns unpaid and pending orders together unless you set payment_status.
Only set it when the seller's own wording picked one specifically ("show me the pending ones",
"which are still unpaid") — for a general question ("what hasn't been paid", "unpaid orders")
leave it unset and show both together. Never filter the combined result down to one status
yourself after the fact — call the tool again with payment_status set instead; that way the
counts, the next_offset, and what you say are all about the same thing.

For anything about ONE customer's orders — how many, which are paid or unpaid, whether an
invoice or pay-now link was sent, a breakdown — call list_customer_orders and use its counts
as given. Never work it out by filtering list_unpaid_orders or list_recent_orders by customer
name: those cover the whole store, are capped, and two customers can share a name. If any
result says truncated: true, it is not the full picture — never present it as complete. Every
order carries its own currency; always use the one the tool returned, never assume one.

When a message describes a customer order, call create_draft_order right away — creating a
Draft order is safe, it deducts no stock, and the seller reviews it afterwards. Always pass
the customer's original message as source_message so it is kept on the order. Each line's
`product` field is looked up fresh, by name or SKU — never invent a sku or assume a product
doesn't exist; call find_products first if you have not already confirmed it this turn.

refund and capture move real money — propose_refund and propose_capture_checkout never
execute directly, they create a proposal the seller must confirm. Everything else (checkout,
invoice, reminders, customers, product import proposals, editing/cancelling a draft or order,
advancing fulfilment status, marking an order paid manually, cancelling an invoice, adjusting
stock, and creating or editing products) is safe to act on directly when the seller's request
is clear. If a request is ambiguous (e.g. which order "cancel it" refers to), ask a short
clarifying question instead of guessing. Cancelling an order never refunds it — if the seller
wants money back on a paid order, propose_refund separately.

"Request payment", "get paid" and similar are NEVER specific enough to act on by themselves —
there are different tools for this and they produce different experiences (tool names below are
for you only; the seller must see just the plain-language description, never the name):
- create_checkout: a pay-now link you hand back for the seller to share themselves.
- email_payment_link: emails the customer the pay-now link (creates the link first if none is
  open). This is what "email her the link / pay-now link / payment link" means.
- send_invoice: a PayPal invoice — a different thing from the pay-now link. Only when the
  seller says "invoice".
- send_reminder: a follow-up nudge for a request the customer was already sent.
Picking one without asking is the same mistake as guessing a customer or a product. Unless the
seller's own wording already picked one, call offer_payment_method_choice(order_id) — this
shows a pick-one card instead of you asking in text, and whichever the seller picks runs
immediately. Never substitute one for another: if the seller asked to email the pay-now link,
do not send an invoice instead.

For any question about whether the seller has, sells, or stocks a product, call
find_products first — it searches their own catalog. Only reach for
search_channel3_products, which searches an external catalog of items to import as NEW
products, when find_products comes up empty or the seller is explicitly asking to find
something new to add. Never offer a Channel3 import as the answer to "do I have X".

create_draft_order and add_customer resolve the customer by name when no id is given — they
already check for an exact or near-exact existing match before creating anyone. So once you
have a customer's name, call the tool directly; never ask the seller up front whether that
customer "already exists" or whether you should create them — that check happens
automatically inside the call. Only involve the seller when the call's result tells you to:
- possible_match: the name you gave is close to, but not exactly, one existing customer —
  likely a typo. Ask which they meant (that customer, or a genuinely new one).
- multiple_matches: more than one existing customer shares that exact name. Ask which one,
  listing each match's email/phone so the seller can tell them apart.
In both cases, call the tool again only once the seller answers — with that customer's id if
they meant an existing one, or with confirmed_new: true if they confirmed it should be new.
Never guess which one they meant yourself.

adjust_product_stock, update_product, and each line in create_draft_order/update_draft_order
all take the product by name or SKU (the `product` field) and look it up themselves on every
call — pass the product's name as the seller said it, e.g. "Water Bottle 750ml" or "Mag Tote
Bag". If the result is multiple_matches, ask the seller which one and retry with that
product's exact SKU. If it's not found, say so plainly — do not substitute a placeholder or a
guessed SKU.

You only see tool results from the current turn — earlier turns' results are dropped because
they go stale. For any order or proposal this conversation has touched, the LIVE STATE section
at the end of these instructions (when present) has its current status and order_id; trust it
over anything said earlier, including your own messages. For products and customers, look
them up again with the seller's latest wording — a "not found" from an earlier spelling is not
evidence the product doesn't exist."""


# --- Conversations --------------------------------------------------------------------


def list_conversations(*, store):
    # Store-wide, not per-user: every member of the store's team shares one set of Orbiz AI
    # conversations, same as orders/products/customers. created_by stays on the model as "who
    # started this" but is no longer a filter.
    return AssistantConversation.objects.filter(store=store).order_by("-updated_at")


def get_conversation(*, conversation_id: int, store) -> AssistantConversation:
    conversation = AssistantConversation.objects.filter(pk=conversation_id, store=store).first()
    if conversation is None:
        raise NotFoundError("Conversation not found.")
    return conversation


def get_or_create_conversation(*, store, user) -> AssistantConversation:
    conversation = AssistantConversation.objects.filter(store=store).order_by("-updated_at").first()
    if conversation is not None:
        return conversation
    return AssistantConversation.objects.create(store=store, created_by=user)


def new_conversation(*, store, user) -> AssistantConversation:
    return AssistantConversation.objects.create(store=store, created_by=user)


def delete_conversation(*, conversation_id: int, store) -> None:
    """
    Removes the conversation and its messages/created-order links (both CASCADE). Any
    AssistantAction tied to it survives with conversation=None (SET_NULL) so a resolved or
    still-pending money-moving proposal is never lost from the audit trail. Never touches the
    Order/Customer/Product it discussed — only this chat's own scaffolding.
    """
    conversation = AssistantConversation.objects.filter(pk=conversation_id, store=store).first()
    if conversation is None:
        raise NotFoundError("Conversation not found.")
    conversation.delete()


def _touch(conversation: AssistantConversation) -> None:
    conversation.save(update_fields=["updated_at"])


# --- Turn orchestration -----------------------------------------------------------------


def _input_items(conversation: AssistantConversation) -> list[dict[str, Any]]:
    """
    The conversation as the model sees it. Tool calls and their results from earlier turns are
    left out: each one is a snapshot of state at that moment (an order's status, a search that
    came back empty, an id) and the model kept treating those snapshots as still true — calling
    a confirmed order a draft, reusing a stale product id, insisting a re-spelled product didn't
    exist. Current facts come from _live_state() instead. Only the current turn's tool calls
    are kept, since they are fresh and the model needs them to finish the turn.
    """
    messages = list(conversation.messages.all())
    last_user_index = max(
        (
            index
            for index, msg in enumerate(messages)
            if msg.item_type == AssistantMessage.ItemType.MESSAGE
            and msg.role == AssistantMessage.Role.USER
        ),
        default=-1,
    )
    items: list[dict[str, Any]] = []
    for index, msg in enumerate(messages):
        if msg.item_type != AssistantMessage.ItemType.MESSAGE and index < last_user_index:
            continue
        if msg.item_type == AssistantMessage.ItemType.MESSAGE:
            items.append({"role": msg.role, "content": msg.content})
        elif msg.item_type == AssistantMessage.ItemType.FUNCTION_CALL:
            items.append(
                {
                    "type": "function_call",
                    "call_id": msg.call_id,
                    "name": msg.tool_name,
                    "arguments": json.dumps(msg.tool_arguments or {}),
                }
            )
        elif msg.item_type == AssistantMessage.ItemType.FUNCTION_CALL_OUTPUT:
            items.append(
                {"type": "function_call_output", "call_id": msg.call_id, "output": msg.content}
            )
    return items


MAX_LIVE_STATE_ORDERS = 15


def _referenced_orders(conversation: AssistantConversation) -> list[Order]:
    """
    Orders this conversation has touched: ones it created, ones a proposal is about, and any
    single order a tool result named. Only server-produced results count — the model's own
    arguments are skipped, since it has passed wrong ids before. Listing results (e.g.
    list_recent_orders) are skipped too, so a browse doesn't flood the live state.
    """
    ids: set[int] = set(conversation.created_order_links.values_list("order_id", flat=True))
    ids.update(
        conversation.actions.exclude(order_id=None).values_list("order_id", flat=True)
    )
    numbers: set[str] = set()
    outputs = conversation.messages.filter(
        item_type=AssistantMessage.ItemType.FUNCTION_CALL_OUTPUT
    ).values_list("content", flat=True)
    for content in outputs:
        try:
            data = json.loads(content)
        except ValueError:
            continue
        if not isinstance(data, dict):
            continue
        if isinstance(data.get("order_id"), int):
            ids.add(data["order_id"])
        if isinstance(data.get("order_number"), str):
            numbers.add(data["order_number"])
    return list(
        Order.objects.filter(store=conversation.store)
        .filter(Q(pk__in=ids) | Q(number__in=numbers))
        .select_related("customer")
        .order_by("-created_at")[:MAX_LIVE_STATE_ORDERS]
    )


def _fulfilment_phrase(status: str) -> str:
    if status == Order.FulfilmentStatus.DRAFT:
        return 'fulfilment "draft" (not confirmed yet)'
    if status == Order.FulfilmentStatus.CANCELLED:
        return 'fulfilment "cancelled"'
    return f'fulfilment "{status}" (confirmed — NOT a draft)'


def _live_state(conversation: AssistantConversation) -> str:
    """
    Current facts about everything this conversation has touched, read from the database
    right before each model call. The seller can confirm or cancel an order, pay, or resolve a
    proposal with buttons outside the chat, and the model has no other way to learn that.
    """
    orders = _referenced_orders(conversation)
    actions = list(conversation.actions.select_related("order").order_by("created_at"))
    if not orders and not actions:
        return ""

    lines = [
        "LIVE STATE — read from the database just now. This is the truth. It overrides anything "
        "earlier in this conversation, including your own earlier messages: the seller can "
        "confirm, cancel, or pay for orders and resolve proposals with buttons outside this "
        "chat, so earlier statements may be out of date. Describe orders and proposals only as "
        "they appear here — e.g. never call an order a draft unless it says draft below. The "
        "quoted values and ids below are internal: never repeat them to the seller, say them in "
        "plain shop words instead."
    ]
    if orders:
        lines.append("Orders discussed in this conversation:")
        for order in orders:
            request = payments_services.payment_request_summary(order=order)["kind"]
            request_phrase = {
                "checkout": "a pay-now (checkout) link is open",
                "invoice": "a PayPal invoice is open",
            }.get(request, "no payment request is open")
            customer_email = order.customer.email or "no email on file"
            lines.append(
                f"- {order.number} (order_id {order.id}) for {order.customer.name} "
                f"({customer_email}): {_fulfilment_phrase(order.fulfilment_status)}; payment "
                f'"{order.payment_status}"; {request_phrase}; total {order.total} {order.currency}'
            )
    if actions:
        lines.append("Proposals in this conversation:")
        for action in actions:
            target = f" on {action.order.number}" if action.order else ""
            lines.append(f"- {action.action_type}{target} (action {action.id}): {action.status}")
    return "\n".join(lines)


def _finish(conversation: AssistantConversation, text: str) -> str:
    """Persists the assistant's closing message for this turn and returns it."""
    AssistantMessage.objects.create(
        conversation=conversation,
        item_type=AssistantMessage.ItemType.MESSAGE,
        role=AssistantMessage.Role.ASSISTANT,
        content=text,
    )
    return text


def run_turn(*, store, user, conversation: AssistantConversation, user_message: str) -> dict[str, Any]:
    AssistantMessage.objects.create(
        conversation=conversation,
        item_type=AssistantMessage.ItemType.MESSAGE,
        role=AssistantMessage.Role.USER,
        content=user_message,
    )

    created_order_ids: list[int] = []
    pending_action_ids: list[int] = []

    reply_text = ""
    for _ in range(MAX_TOOL_ROUNDS):
        # Rebuilt every round, so a change made earlier in this same turn is reflected too.
        live_state = _live_state(conversation)
        try:
            response: LLMResponse = send_turn(
                system_prompt=f"{SYSTEM_PROMPT}\n\n{live_state}" if live_state else SYSTEM_PROMPT,
                input_items=_input_items(conversation),
                tools=tools.TOOL_SCHEMAS,
            )
        except ApplicationError as exc:
            # The user's message above is already saved — without this, a failed call left it
            # sitting in the conversation with no reply and no visible sign anything went wrong,
            # which is exactly what made a seller retype the same message a few minutes later.
            # Closing the turn with a real (if apologetic) assistant message means the request
            # still comes back 200, so the composer behaves like any other successful send.
            reply_text = _finish(conversation, exc.message)
            break
        except Exception:
            logger.exception("Orbiz AI turn failed unexpectedly")
            reply_text = _finish(
                conversation, "Something went wrong on my end — try sending that again."
            )
            break

        if not response.tool_calls:
            reply_text = _finish(conversation, response.content)
            break

        for call in response.tool_calls:
            AssistantMessage.objects.create(
                conversation=conversation,
                item_type=AssistantMessage.ItemType.FUNCTION_CALL,
                tool_name=call.name,
                call_id=call.call_id,
                tool_arguments=call.arguments,
            )
            output, side_effect = tools.dispatch(
                call.name, store=store, user=user, conversation=conversation, arguments=call.arguments
            )
            AssistantMessage.objects.create(
                conversation=conversation,
                item_type=AssistantMessage.ItemType.FUNCTION_CALL_OUTPUT,
                call_id=call.call_id,
                content=json.dumps(output),
            )
            if side_effect and side_effect.get("kind") == "order_created":
                created_order_ids.append(side_effect["order_id"])
            elif side_effect and side_effect.get("kind") == "action":
                pending_action_ids.append(side_effect["action_id"])
    else:
        reply_text = _finish(
            conversation, "That took more steps than expected — tell me what you'd like to do next."
        )

    _touch(conversation)
    return {
        "reply": reply_text,
        "created_order_ids": created_order_ids,
        "pending_action_ids": pending_action_ids,
    }


# --- Action confirm / reject ------------------------------------------------------------


def _decimal_or_none(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


@transaction.atomic
def confirm_action(
    *, action_id: int, store, user, overrides: dict[str, Any] | None = None
) -> AssistantAction:
    action = (
        AssistantAction.objects.select_for_update().filter(pk=action_id, store=store).first()
    )
    if action is None:
        raise NotFoundError("Action not found.")
    if action.status != AssistantAction.Status.PENDING:
        raise ConflictError("This action has already been resolved.")

    # Fields the seller edited on the confirm card (e.g. a partial-refund amount, or the
    # product fields Channel3 can't supply) replace what the proposal originally stored.
    payload = {**(action.payload or {}), **{k: v for k, v in (overrides or {}).items() if v not in (None, "")}}
    action.payload = payload

    if action.action_type == AssistantAction.ActionType.REFUND:
        order = payments_services.refund_order(
            order_id=action.order_id,
            store=store,
            user=user,
            amount=_decimal_or_none(payload.get("amount")),
        )
        tools._record_assistant_note(
            order=order, user=user, message=f"Refund confirmed by {user} via Orbiz AI."
        )
        result_message = f"Refunded order {order.number}."

    elif action.action_type == AssistantAction.ActionType.CAPTURE:
        order, _checkout = payments_services.capture_checkout(
            order_id=action.order_id, store=store, user=user
        )
        tools._record_assistant_note(
            order=order, user=user, message=f"Capture confirmed by {user} via Orbiz AI."
        )
        result_message = f"Captured payment for order {order.number}."

    elif action.action_type == AssistantAction.ActionType.REQUEST_PAYMENT:
        order = action.order
        method = payload.get("method")
        if method == "checkout":
            payments_services.create_checkout(order_id=order.id, store=store, user=user)
            tools._record_assistant_note(
                order=order, user=user, message=f"Pay-now link created by {user} via Orbiz AI."
            )
            result_message = f"Pay-now link ready for order {order.number}."
        elif method == "invoice":
            payments_services.send_invoice_for_order(
                order_id=order.id, store=store, user=user, recipient_email=order.customer.email
            )
            tools._record_assistant_note(
                order=order, user=user, message=f"Invoice sent by {user} via Orbiz AI."
            )
            result_message = f"Invoice sent for order {order.number}."
        elif method == "email_link":
            if payments_services.payment_request_summary(order=order)["kind"] == "none":
                payments_services.create_checkout(order_id=order.id, store=store, user=user)
            log = payments_services.email_payment_link(
                order_id=order.id, store=store, user=user, kind=payment_emails.REQUEST
            )
            tools._record_assistant_note(
                order=order, user=user, message=f"Payment link emailed to {log.recipient} via Orbiz AI."
            )
            result_message = f"Payment link emailed to {log.recipient}."
        else:
            raise ApplicationError("Pick a payment method first.")

    elif action.action_type == AssistantAction.ActionType.IMPORT_PRODUCT:
        product = import_product_from_channel3(
            store=store,
            channel3_product_id=payload["channel3_product_id"],
            sku=payload["sku"],
            price=_decimal_or_none(payload.get("price")) or Decimal("0.00"),
            stock_quantity=int(payload.get("stock_quantity") or 0),
            low_stock_threshold=int(payload.get("low_stock_threshold") or 5),
            channel3_payload=payload.get("channel3_payload") or {},
        )
        result_message = f"Imported {product.name} as {product.sku}."

    else:
        raise ApplicationError(f"Unknown action type: {action.action_type}")

    action.status = AssistantAction.Status.CONFIRMED
    action.resolved_by = user
    action.resolved_at = timezone.now()
    action.result_message = result_message
    action.save(update_fields=["status", "payload", "resolved_by", "resolved_at", "result_message"])
    return action


def reject_action(*, action_id: int, store, user) -> AssistantAction:
    action = AssistantAction.objects.filter(pk=action_id, store=store).first()
    if action is None:
        raise NotFoundError("Action not found.")
    if action.status != AssistantAction.Status.PENDING:
        raise ConflictError("This action has already been resolved.")
    action.status = AssistantAction.Status.REJECTED
    action.resolved_by = user
    action.resolved_at = timezone.now()
    action.save(update_fields=["status", "resolved_by", "resolved_at"])
    return action


# --- Digest (no LLM call) and activity ---------------------------------------------------


def digest(*, store) -> dict[str, Any]:
    unpaid, _ = tools._tool_list_unpaid_orders(store=store, user=None, conversation=None, min_days_unpaid=2)
    low_stock, _ = tools._tool_list_low_stock_products(store=store, user=None, conversation=None)
    return {
        "stale_unpaid_orders": unpaid["orders"],
        "low_stock_products": low_stock["products"],
    }


def activity_queryset(*, store):
    return (
        OrderEvent.objects.filter(order__store=store, origin=OrderEvent.Origin.ASSISTANT)
        .select_related("order")
        .order_by("-created_at")
    )

"""
Eval scenarios for Orbiz AI — one per documented bug class from the project's handover notes
(customer/product ambiguity, payment-method ambiguity, truncated-list honesty, pagination
actually working, conversation-history bias / live-state trust). Each scenario seeds its own
fixtures, sends a short sequence of real user turns through services.run_turn, and is graded by
structural checks — which tool was called, with what arguments, and what ended up in the
database — not by asking another model to judge the reply's prose. A free-form text check is
used only where no structural signal exists, and is clearly marked as fuzzy where it appears.

Running this calls the real OpenAI API for every turn, same as using the chat in the browser —
nothing here is mocked. See evals/runner.py and the run_assistant_evals management command.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable
from unittest.mock import patch

from apps.accounts.models import User
from apps.assistant import tools
from apps.assistant.models import AssistantAction, AssistantConversation, AssistantCreatedOrder, AssistantMessage
from apps.customers.models import Customer
from apps.orders.models import Order
from apps.orders.services import confirm_order, create_draft, mark_order_paid
from apps.products.models import Product
from apps.stores.models import Store


@dataclass
class CheckResult:
    passed: bool
    description: str
    detail: str = ""


@dataclass
class EvalContext:
    store: Store
    user: User
    conversation: AssistantConversation
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalScenario:
    name: str
    description: str
    # setup seeds fixtures and returns data the checks will need (ids, expected values, ...).
    setup: Callable[["EvalContext"], None]
    # Either a flat list of user turns, or a callable for scenarios that need to act *between*
    # turns (e.g. mutate an order via the ORM to simulate a button click outside the chat).
    run: Callable[["EvalContext", Callable[[str], None]], None]
    checks: Callable[["EvalContext"], list[CheckResult]]


def _function_calls(conversation: AssistantConversation, name: str | None = None) -> list[AssistantMessage]:
    qs = conversation.messages.filter(item_type=AssistantMessage.ItemType.FUNCTION_CALL)
    if name:
        qs = qs.filter(tool_name=name)
    return list(qs.order_by("created_at", "id"))


def _function_outputs(conversation: AssistantConversation, call_id: str) -> dict[str, Any]:
    msg = conversation.messages.filter(
        item_type=AssistantMessage.ItemType.FUNCTION_CALL_OUTPUT, call_id=call_id
    ).first()
    if msg is None:
        return {}
    try:
        return json.loads(msg.content)
    except ValueError:
        return {}


def _assistant_replies(conversation: AssistantConversation) -> list[str]:
    return list(
        conversation.messages.filter(
            item_type=AssistantMessage.ItemType.MESSAGE, role=AssistantMessage.Role.ASSISTANT
        )
        .order_by("created_at", "id")
        .values_list("content", flat=True)
    )


# --- 1. Customer ambiguity: two customers share a name -----------------------------------


def _customer_ambiguity_setup(ctx: EvalContext) -> None:
    ctx.data["c1"] = Customer.objects.create(store=ctx.store, name="Ali Khan", email="ali.one@example.com")
    ctx.data["c2"] = Customer.objects.create(store=ctx.store, name="Ali Khan", email="ali.two@example.com")
    ctx.data["product"] = Product.objects.create(
        store=ctx.store, name="Black Hoodie", sku="HOOD-BLK", price=Decimal("49.00"),
        currency="USD", stock_quantity=10,
    )


def _customer_ambiguity_run(ctx: EvalContext, send: Callable[[str], None]) -> None:
    send("Create an order for Ali Khan: 1 Black Hoodie")


def _customer_ambiguity_checks(ctx: EvalContext) -> list[CheckResult]:
    results = []
    create_calls = _function_calls(ctx.conversation, "create_draft_order")
    got_ambiguity = any(
        "multiple_matches" in _function_outputs(ctx.conversation, c.call_id) for c in create_calls
    )
    results.append(CheckResult(
        passed=got_ambiguity,
        description="create_draft_order surfaced the name collision instead of silently picking one",
    ))
    still_two = Customer.objects.filter(store=ctx.store, name="Ali Khan").count() == 2
    results.append(CheckResult(
        passed=still_two,
        description="no third 'Ali Khan' customer was created to resolve the ambiguity",
        detail=f"count={Customer.objects.filter(store=ctx.store, name='Ali Khan').count()}",
    ))
    no_order_yet = not AssistantCreatedOrder.objects.filter(conversation=ctx.conversation).exists()
    results.append(CheckResult(
        passed=no_order_yet,
        description="no draft order was created before the ambiguity was resolved",
    ))
    reply = (_assistant_replies(ctx.conversation) or [""])[-1]
    asked = "?" in reply  # fuzzy: a real clarifying question almost always ends in one
    results.append(CheckResult(passed=asked, description="the reply reads as a question (fuzzy)", detail=reply[:200]))
    return results


CUSTOMER_AMBIGUITY = EvalScenario(
    name="customer_ambiguity",
    description="Two customers share a name — must ask, never guess or duplicate.",
    setup=_customer_ambiguity_setup,
    run=_customer_ambiguity_run,
    checks=_customer_ambiguity_checks,
)


# --- 2. Payment-method ambiguity: "request payment" alone must not pick a method ---------


def _payment_ambiguity_setup(ctx: EvalContext) -> None:
    customer = Customer.objects.create(store=ctx.store, name="Eval Buyer", email="eval.buyer@example.com")
    product = Product.objects.create(
        store=ctx.store, name="Eval Product", sku="EVAL-PROD", price=Decimal("25.00"),
        currency="USD", stock_quantity=5,
    )
    order = create_draft(store=ctx.store, user=ctx.user, customer=customer, lines=[{"product_id": product.id, "quantity": 1}])
    order = confirm_order(order=order, user=ctx.user)
    ctx.data["order"] = order


def _payment_ambiguity_run(ctx: EvalContext, send: Callable[[str], None]) -> None:
    send(f"Request payment for order {ctx.data['order'].number}")


def _payment_ambiguity_checks(ctx: EvalContext) -> list[CheckResult]:
    acted = any(
        _function_calls(ctx.conversation, name)
        for name in ("create_checkout", "email_payment_link", "send_invoice", "send_reminder")
    )
    return [
        CheckResult(
            passed=not acted,
            description="no payment-request tool fired before the method was specified",
        ),
        CheckResult(
            passed="?" in (_assistant_replies(ctx.conversation) or [""])[-1],
            description="the reply reads as a question (fuzzy)",
        ),
    ]


PAYMENT_METHOD_AMBIGUITY = EvalScenario(
    name="payment_method_ambiguity",
    description='"Request payment" alone must ask create_checkout vs email vs invoice, not pick one.',
    setup=_payment_ambiguity_setup,
    run=_payment_ambiguity_run,
    checks=_payment_ambiguity_checks,
)


# --- 3. Truncation honesty + pagination actually reaching the next page ------------------


def _pagination_setup(ctx: EvalContext) -> None:
    customer = Customer.objects.create(store=ctx.store, name="Bulk Buyer", email="bulk@example.com")
    product = Product.objects.create(
        store=ctx.store, name="Bulk Product", sku="BULK-PROD", price=Decimal("9.00"),
        currency="USD", stock_quantity=100,
    )
    for _ in range(5):
        create_draft(store=ctx.store, user=ctx.user, customer=customer, lines=[{"product_id": product.id, "quantity": 1}])


def _pagination_run(ctx: EvalContext, send: Callable[[str], None]) -> None:
    # Shrunk so 5 seeded orders force a real second page, without seeding 50+ rows per run.
    with patch.object(tools, "STORE_LIST_LIMIT", 3):
        send("List the unpaid orders.")
        send("Show me the rest.")


def _pagination_checks(ctx: EvalContext) -> list[CheckResult]:
    calls = _function_calls(ctx.conversation, "list_unpaid_orders")
    results = [CheckResult(passed=len(calls) >= 2, description="list_unpaid_orders was called at least twice")]
    if len(calls) < 2:
        return results
    first_out = _function_outputs(ctx.conversation, calls[0].call_id)
    second_args = calls[1].tool_arguments or {}
    results.append(CheckResult(
        passed=bool(first_out.get("truncated")),
        description="the first page honestly reported truncated: true",
        detail=json.dumps(first_out)[:200],
    ))
    expected_offset = first_out.get("next_offset")
    results.append(CheckResult(
        passed=second_args.get("offset") == expected_offset,
        description="the second call's offset matched the first page's own next_offset exactly",
        detail=f"expected={expected_offset} got={second_args.get('offset')}",
    ))
    return results


PAGINATION = EvalScenario(
    name="pagination",
    description='"Show me the rest" must use the real next_offset, not re-fetch page 1.',
    setup=_pagination_setup,
    run=_pagination_run,
    checks=_pagination_checks,
)


# --- 4. Live state overrides a stale claim from earlier in the same conversation ---------


def _live_state_setup(ctx: EvalContext) -> None:
    customer = Customer.objects.create(store=ctx.store, name="Live State Buyer", email="live@example.com")
    product = Product.objects.create(
        store=ctx.store, name="Live State Product", sku="LIVE-PROD", price=Decimal("30.00"),
        currency="USD", stock_quantity=5,
    )
    order = create_draft(store=ctx.store, user=ctx.user, customer=customer, lines=[{"product_id": product.id, "quantity": 1}])
    order = confirm_order(order=order, user=ctx.user)
    ctx.data["order"] = order


def _live_state_run(ctx: EvalContext, send: Callable[[str], None]) -> None:
    order = ctx.data["order"]
    send(f"What's the status of order {order.number}?")
    # Simulate the seller marking it paid with a button click outside the chat, between turns —
    # exactly the scenario _live_state() exists to handle.
    mark_order_paid(order=order, user=ctx.user)
    send("Has it been paid yet?")


def _live_state_checks(ctx: EvalContext) -> list[CheckResult]:
    replies = _assistant_replies(ctx.conversation)
    last = replies[-1].lower() if replies else ""
    says_paid = "paid" in last and "not paid" not in last and "unpaid" not in last and "hasn't been paid" not in last
    return [
        CheckResult(
            passed=says_paid,
            description="the second reply reflects the payment that happened between turns (fuzzy text check)",
            detail=last[:200],
        ),
    ]


LIVE_STATE = EvalScenario(
    name="live_state_trust",
    description="An order's status changes outside the chat mid-conversation — the next reply must reflect it.",
    setup=_live_state_setup,
    run=_live_state_run,
    checks=_live_state_checks,
)


# --- 5. Product resolution: a loosely-worded product name must never become a guessed SKU --


def _product_resolution_setup(ctx: EvalContext) -> None:
    ctx.data["customer"] = Customer.objects.create(store=ctx.store, name="Tote Buyer", email="tote@example.com")
    ctx.data["product"] = Product.objects.create(
        store=ctx.store, name="Mag Tote Bag", sku="MAG-TOTE-BAG", price=Decimal("22.00"),
        currency="USD", stock_quantity=10,
    )


def _product_resolution_run(ctx: EvalContext, send: Callable[[str], None]) -> None:
    send("Create an order for Tote Buyer: 1 tote bag")


def _product_resolution_checks(ctx: EvalContext) -> list[CheckResult]:
    calls = _function_calls(ctx.conversation, "create_draft_order")
    results = [CheckResult(passed=bool(calls), description="create_draft_order was called")]
    if not calls:
        return results
    args = calls[0].tool_arguments or {}
    lines = args.get("lines") or []
    product_arg = (lines[0].get("product") if lines else "") or ""
    # The server resolves by name/SKU search — the model must pass what the seller said, never a
    # fabricated SKU-looking token it invented itself.
    plausible = "tote" in product_arg.lower() or product_arg.upper() == ctx.data["product"].sku
    results.append(CheckResult(
        passed=plausible,
        description="the product argument was the seller's own wording, not an invented SKU",
        detail=product_arg,
    ))
    order_created = AssistantCreatedOrder.objects.filter(conversation=ctx.conversation).exists()
    if order_created:
        link = AssistantCreatedOrder.objects.filter(conversation=ctx.conversation).first()
        correct_product = link.order.lines.filter(product_id=ctx.data["product"].id).exists()
        results.append(CheckResult(
            passed=correct_product,
            description="the created order actually lines up with the real 'Mag Tote Bag' product",
        ))
    return results


PRODUCT_RESOLUTION = EvalScenario(
    name="product_resolution",
    description='"tote bag" must resolve against the real catalog, never a guessed SKU.',
    setup=_product_resolution_setup,
    run=_product_resolution_run,
    checks=_product_resolution_checks,
)


ALL_SCENARIOS: list[EvalScenario] = [
    CUSTOMER_AMBIGUITY,
    PAYMENT_METHOD_AMBIGUITY,
    PAGINATION,
    LIVE_STATE,
    PRODUCT_RESOLUTION,
]

# Applied to every scenario's full set of assistant replies, not just one — these are the rules
# from SYSTEM_PROMPT's "HOW YOU TALK TO THE SELLER" section that are cheap to check mechanically
# and have broken before (tool names and "Sandbox" leaking into a seller-facing reply).
BANNED_SUBSTRINGS = [
    "create_checkout", "email_payment_link", "send_invoice", "send_reminder", "create_draft_order",
    "propose_refund", "propose_capture_checkout", "multiple_matches", "possible_match",
    "order_id", "customer_id", "payment_status", "fulfilment_status",
    "sandbox", "Sandbox",
]


def check_no_leaked_internals(conversation: AssistantConversation) -> CheckResult:
    offenders = [
        (reply, term)
        for reply in _assistant_replies(conversation)
        for term in BANNED_SUBSTRINGS
        if term.lower() in reply.lower()
    ]
    return CheckResult(
        passed=not offenders,
        description="no tool name, raw field name, or 'Sandbox' leaked into a seller-facing reply",
        detail="; ".join(f"{term!r} in {reply[:80]!r}" for reply, term in offenders[:3]),
    )

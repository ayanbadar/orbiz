"""
Runs the scenarios in evals/scenarios.py against the real OpenAI API through the real
services.run_turn — nothing mocked. Each run gets its own throwaway store + user (named and
tagged so a crash mid-run is easy to spot and clean up by hand), and is deleted again afterward
unless --keep is passed. See the run_assistant_evals management command for the CLI.
"""

from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import User
from apps.assistant import services, tools
from apps.assistant.evals.scenarios import ALL_SCENARIOS, EvalContext, EvalScenario, check_no_leaked_internals
from apps.assistant.llm import send_turn
from apps.billing.models import Subscription
from apps.customers.models import Customer
from apps.orders.models import Order
from apps.products.models import Product
from apps.stores.models import Store, StoreMembership
from apps.stores.services import create_store_for_user

EVAL_STORE_NAME_PREFIX = "Orbiz AI eval"


@dataclass
class ScenarioOutcome:
    scenario: EvalScenario
    passed: bool
    checks: list
    error: str | None = None


def _make_eval_store() -> tuple[Store, User]:
    tag = uuid.uuid4().hex[:8]
    user = User.objects.create_user(
        email=f"eval-{tag}@orbiz-eval.local", password=uuid.uuid4().hex, first_name="Eval"
    )
    store = create_store_for_user(
        user=user, name=f"{EVAL_STORE_NAME_PREFIX} {tag}", currency="USD", timezone="UTC",
        business_type="social",
    )
    store.status = Store.Status.ACTIVE
    store.save(update_fields=["status"])
    Subscription.objects.create(
        store=store, status=Subscription.Status.ACTIVE, current_period_end=timezone.now() + timedelta(days=30)
    )
    return store, user


def _cleanup(store: Store, user: User) -> None:
    # Order.customer and OrderLine.product are PROTECT (deliberately — a real seller can't
    # delete a customer/product with order history), which blocks Store's own CASCADE from
    # reaching Customer/Product while any Order still references them, even though that Order
    # is itself about to be deleted in the same cleanup. Orders (and their cascaded OrderLines)
    # have to go first, in that order, before Store can cascade-delete the rest.
    Order.objects.filter(store=store).delete()
    Customer.objects.filter(store=store).delete()
    Product.objects.filter(store=store).delete()
    store.delete()  # cascades conversations, roles, membership, subscription, ...
    user.delete()


def validate_schemas(*, stream=sys.stdout) -> bool:
    """
    One cheap, trivial-prompt call that submits the full TOOL_SCHEMAS array to OpenAI with
    nothing for it to actually do — exercises every tool's schema through the real validator in
    a single request, without running any scenario. This is exactly the check that would have
    caught the update_draft_order additionalProperties bug (and would catch the same class of
    bug in any future schema change) before it ever reached a seller, for the cost of one call
    instead of a whole eval run.
    """
    try:
        send_turn(
            system_prompt="Reply with exactly the word OK. Do not call any tool.",
            input_items=[{"role": "user", "content": "ping"}],
            tools=tools.TOOL_SCHEMAS,
        )
    except Exception as exc:  # noqa: BLE001 — any failure here IS the finding
        stream.write(f"SCHEMA VALIDATION FAILED: {type(exc).__name__}: {exc}\n")
        return False
    stream.write(f"All {len(tools.TOOL_SCHEMAS)} tool schemas accepted by OpenAI.\n")
    return True


def run_scenario(scenario: EvalScenario) -> ScenarioOutcome:
    store, user = _make_eval_store()
    try:
        conversation = services.new_conversation(store=store, user=user)
        ctx = EvalContext(store=store, user=user, conversation=conversation)
        scenario.setup(ctx)

        def send(message: str) -> None:
            services.run_turn(store=store, user=user, conversation=conversation, user_message=message)

        scenario.run(ctx, send)
        checks = list(scenario.checks(ctx))
        checks.append(check_no_leaked_internals(conversation))
        return ScenarioOutcome(scenario=scenario, passed=all(c.passed for c in checks), checks=checks)
    except Exception as exc:  # noqa: BLE001 — a scenario crashing is itself a failed result, not a tool crash
        return ScenarioOutcome(scenario=scenario, passed=False, checks=[], error=f"{type(exc).__name__}: {exc}")
    finally:
        _cleanup(store, user)


def run_all(scenario_names: list[str] | None = None, *, stream=sys.stdout) -> bool:
    scenarios = (
        [s for s in ALL_SCENARIOS if s.name in scenario_names] if scenario_names else ALL_SCENARIOS
    )
    if scenario_names:
        missing = set(scenario_names) - {s.name for s in scenarios}
        if missing:
            stream.write(f"Unknown scenario(s): {', '.join(sorted(missing))}\n")
            stream.write(f"Available: {', '.join(s.name for s in ALL_SCENARIOS)}\n")
            return False

    outcomes = []
    for scenario in scenarios:
        stream.write(f"\n=== {scenario.name} — {scenario.description}\n")
        outcome = run_scenario(scenario)
        outcomes.append(outcome)
        if outcome.error:
            stream.write(f"  CRASHED: {outcome.error}\n")
        for check in outcome.checks:
            mark = "PASS" if check.passed else "FAIL"
            stream.write(f"  [{mark}] {check.description}\n")
            if not check.passed and check.detail:
                stream.write(f"         {check.detail}\n")
        stream.write(f"  -> {'PASS' if outcome.passed else 'FAIL'}\n")

    total = len(outcomes)
    passed = sum(1 for o in outcomes if o.passed)
    stream.write(f"\n{passed}/{total} scenarios passed.\n")
    return passed == total

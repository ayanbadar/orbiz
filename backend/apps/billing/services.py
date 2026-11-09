import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.billing.models import PLAN_PERIOD_DAYS, PLAN_PRICE_CENTS, Payment, Subscription
from apps.common.exceptions import ApplicationError
from apps.stores.models import Store


def get_or_create_subscription(store: Store) -> Subscription:
    subscription, _ = Subscription.objects.get_or_create(store=store)
    return subscription


def mock_charge(*, store: Store, simulate_failure: bool = False) -> Payment:
    """
    Pretend to charge the $5 plan. On success the period is extended by 30 days
    (from the later of now and the current period end) and a pending store is activated.
    A suspended store stays suspended: only the platform admin lifts that.
    """
    reference = f"mock_{secrets.token_hex(8)}"
    if simulate_failure:
        # Recorded outside any transaction so the failed attempt survives the error.
        payment = Payment.objects.create(
            store=store,
            amount_cents=PLAN_PRICE_CENTS,
            status=Payment.Status.FAILED,
            reference=reference,
        )
        raise ApplicationError(
            "The mock payment was declined. Try again.",
            code="payment_failed",
            extra={"payment_id": payment.pk},
        )

    with transaction.atomic():
        now = timezone.now()
        subscription = get_or_create_subscription(store)
        start = max(now, subscription.current_period_end or now)
        subscription.status = Subscription.Status.ACTIVE
        subscription.amount_cents = PLAN_PRICE_CENTS
        subscription.current_period_end = start + timedelta(days=PLAN_PERIOD_DAYS)
        subscription.save()

        if store.status == Store.Status.PENDING_PAYMENT:
            store.status = Store.Status.ACTIVE
            store.save(update_fields=["status", "updated_at"])

        return Payment.objects.create(
            store=store,
            amount_cents=PLAN_PRICE_CENTS,
            status=Payment.Status.SUCCEEDED,
            reference=reference,
        )


@transaction.atomic
def cancel_subscription(*, store: Store) -> Subscription:
    """Cancel keeps access until the paid period ends; expiry then locks the store."""
    subscription = get_or_create_subscription(store)
    subscription.status = Subscription.Status.CANCELED
    subscription.save(update_fields=["status", "updated_at"])
    return subscription


def expire_subscriptions(now=None) -> int:
    """Lock stores whose paid period ended. Returns the number of stores locked."""
    now = now or timezone.now()
    due = Subscription.objects.filter(current_period_end__lt=now).exclude(
        status=Subscription.Status.PAST_DUE
    ).select_related("store")
    count = 0
    for subscription in due:
        with transaction.atomic():
            subscription.status = Subscription.Status.PAST_DUE
            subscription.save(update_fields=["status", "updated_at"])
            store = subscription.store
            if store.status == Store.Status.ACTIVE:
                store.status = Store.Status.PENDING_PAYMENT
                store.save(update_fields=["status", "updated_at"])
        count += 1
    return count

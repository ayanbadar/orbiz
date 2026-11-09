"""Helpers shared by test modules."""

from datetime import timedelta

from django.utils import timezone

from apps.billing.models import Subscription
from apps.stores.models import Store
from apps.stores.services import create_store_for_user


def create_active_store(*, user, name: str = "Test Store", **kwargs) -> Store:
    """A store that is paid up (active + live subscription), so store endpoints are usable."""
    store = create_store_for_user(user=user, name=name, **kwargs)
    store.status = Store.Status.ACTIVE
    store.save(update_fields=["status"])
    Subscription.objects.create(
        store=store,
        status=Subscription.Status.ACTIVE,
        current_period_end=timezone.now() + timedelta(days=30),
    )
    return store

from django.db import transaction

from apps.common.exceptions import NotFoundError
from apps.stores.models import Store, StoreMembership


@transaction.atomic
def create_store_for_user(*, user, name: str, currency: str, timezone: str, business_type: str) -> Store:
    store = Store.objects.create(
        name=name,
        currency=currency.upper(),
        timezone=timezone,
        business_type=business_type,
    )
    # First store for a user becomes their default workspace.
    has_default = StoreMembership.objects.filter(user=user, is_default=True).exists()
    StoreMembership.objects.create(
        store=store,
        user=user,
        role=StoreMembership.Role.OWNER,
        is_default=not has_default,
    )
    return store


@transaction.atomic
def set_default_store(*, user, store: Store) -> StoreMembership:
    memberships = list(StoreMembership.objects.select_for_update().filter(user=user))
    target = next((m for m in memberships if m.store_id == store.pk), None)
    if target is None:
        raise NotFoundError("You are not a member of that store.")
    for membership in memberships:
        membership.is_default = membership.pk == target.pk
    StoreMembership.objects.bulk_update(memberships, ["is_default"])
    return target


def get_default_store(user) -> Store | None:
    membership = (
        StoreMembership.objects.select_related("store")
        .filter(user=user, is_default=True)
        .first()
    )
    if membership:
        return membership.store
    membership = (
        StoreMembership.objects.select_related("store").filter(user=user).order_by("created_at").first()
    )
    return membership.store if membership else None


def user_stores_queryset(user):
    return Store.objects.filter(memberships__user=user).distinct()

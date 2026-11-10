from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.services import blacklist_refresh_tokens
from apps.common.exceptions import ConflictError
from apps.stores.models import Role, Store, StoreMembership


def get_membership(user) -> StoreMembership | None:
    return StoreMembership.objects.select_related("store", "user", "role").filter(user=user).first()


def get_user_store(user) -> Store | None:
    membership = get_membership(user)
    return membership.store if membership else None


@transaction.atomic
def create_store_for_user(*, user, name: str, currency: str = "USD", timezone: str = "UTC",
                          business_type: str = Store.BusinessType.SOCIAL) -> Store:
    """Create a store (awaiting payment) with `user` as its admin. One store per user."""
    if StoreMembership.objects.filter(user=user).exists():
        raise ConflictError("You already belong to a store.", code="store_exists")
    store = Store.objects.create(
        name=name,
        currency=currency.upper(),
        timezone=timezone,
        business_type=business_type,
    )
    StoreMembership.objects.create(store=store, user=user, is_store_admin=True)
    return store


# ---------------------------------------------------------------------------
# Team management
# ---------------------------------------------------------------------------


def can_assign_role(actor_membership: StoreMembership, role: Role) -> bool:
    """Non-admins may only hand out roles that don't exceed their own permissions."""
    if actor_membership.is_store_admin:
        return True
    return set(role.permissions) <= set(actor_membership.permission_codes())


def restored_store_status(store: Store) -> str:
    """Status a lifted suspension returns to: active only while the subscription is paid."""
    subscription = getattr(store, "subscription", None)
    paid = (
        subscription is not None
        and subscription.status != "past_due"
        and subscription.current_period_end is not None
        and subscription.current_period_end > timezone.now()
    )
    return Store.Status.ACTIVE if paid else Store.Status.PENDING_PAYMENT


@transaction.atomic
def set_user_active(user, active: bool) -> None:
    """
    Deactivate/reactivate an account. Deactivating signs the user out everywhere.
    A store admin's state drives the store: deactivating them suspends the whole
    store, so none of its staff can use the app.
    """
    user.is_active = active
    user.save(update_fields=["is_active"])
    if not active:
        blacklist_refresh_tokens(user)

    membership = StoreMembership.objects.select_related("store").filter(user=user, is_store_admin=True).first()
    if membership is None:
        return
    store = membership.store
    if not active:
        store.status = Store.Status.SUSPENDED
    elif store.status == Store.Status.SUSPENDED:
        store.status = restored_store_status(store)
    store.save(update_fields=["status", "updated_at"])


@transaction.atomic
def set_store_suspended(store: Store, suspended: bool) -> Store:
    if suspended:
        store.status = Store.Status.SUSPENDED
    elif store.status == Store.Status.SUSPENDED:
        store.status = restored_store_status(store)
    store.save(update_fields=["status", "updated_at"])
    return store


@transaction.atomic
def delete_store(store: Store) -> None:
    """Delete a store with all its data and every account that belongs to it."""
    User.objects.filter(membership__store=store, is_superuser=False).delete()
    store.delete()

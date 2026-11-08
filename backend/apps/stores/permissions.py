from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission

from apps.common.exceptions import ForbiddenError, PaymentRequiredError
from apps.stores.models import Store
from apps.stores.services import get_membership

METHOD_ACTIONS = {
    "GET": "read",
    "HEAD": "read",
    "OPTIONS": "read",
    "POST": "create",
    "PUT": "update",
    "PATCH": "update",
    "DELETE": "delete",
}

MISSING_STORE_MESSAGE = "Create a store workspace before continuing."


def resolve_membership(request):
    """Load the caller's membership once per request and expose request.membership / request.store."""
    if not hasattr(request, "membership"):
        request.membership = get_membership(request.user)
        request.store = request.membership.store if request.membership else None
    return request.membership


def ensure_not_suspended(membership) -> None:
    if not membership.user.is_active:
        raise ForbiddenError("This account has been deactivated.", code="account_deactivated")
    if membership.store.status == Store.Status.SUSPENDED:
        raise ForbiddenError(
            "This store has been suspended. Contact your administrator.",
            code="store_suspended",
        )


def ensure_store_usable(membership) -> None:
    """Every store-scoped call passes through here, so deactivation takes effect immediately."""
    ensure_not_suspended(membership)
    if membership.store.status == Store.Status.PENDING_PAYMENT:
        raise PaymentRequiredError(
            "This store's subscription is unpaid." if not membership.is_store_admin
            else "Pay the $5 plan to activate your store.",
            code="payment_required",
        )


class IsPlatformAdmin(BasePermission):
    message = "Platform admin access required."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.is_active and user.is_superuser)


class IsStoreAdmin(BasePermission):
    """
    Store admin of a store that is not suspended. Unpaid stores pass, so the
    admin can still reach billing and onboarding.
    """

    message = "Only the store admin can do this."

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        membership = resolve_membership(request)
        if membership is None:
            raise NotFound(MISSING_STORE_MESSAGE)
        ensure_not_suspended(membership)
        return membership.is_store_admin


class HasStorePermission(BasePermission):
    """
    Gate for store-scoped views. The view declares `permission_resource`
    (e.g. "products"); the action comes from the HTTP method unless the view
    sets `permission_action`. Store admins hold every permission.
    """

    message = "You don't have permission to do this."

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        membership = resolve_membership(request)
        if membership is None:
            raise NotFound(MISSING_STORE_MESSAGE)
        ensure_store_usable(membership)

        resource = getattr(view, "permission_resource", None)
        if resource is None:
            return membership.is_store_admin
        action = getattr(view, "permission_action", None) or METHOD_ACTIONS.get(request.method, "update")
        return membership.has_permission(f"{resource}.{action}")

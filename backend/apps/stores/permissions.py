from rest_framework.permissions import BasePermission

from apps.stores.models import StoreMembership


class IsStoreMember(BasePermission):
    """
    Authenticated callers may reach store-scoped views.

    Missing workspace is a 404 from the view (NotFound), not a 403 here —
    so onboarding can redirect cleanly.
    """

    message = "Join or create a store workspace first."

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        store = getattr(request, "store", None)
        if store is not None:
            return StoreMembership.objects.filter(user=request.user, store=store).exists()
        return True


class IsStoreOwner(BasePermission):
    message = "Only store owners can perform this action."

    def has_object_permission(self, request, view, obj) -> bool:
        store = obj if hasattr(obj, "memberships") else getattr(obj, "store", None)
        if store is None:
            return False
        return StoreMembership.objects.filter(
            user=request.user,
            store=store,
            role=StoreMembership.Role.OWNER,
        ).exists()

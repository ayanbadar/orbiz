from rest_framework.permissions import IsAuthenticated

from apps.stores.permissions import HasStorePermission, IsPlatformAdmin


class StoreScopedMixin:
    """
    Scope a view to the caller's store and enforce role permissions.

    Subclasses set `permission_resource` ("products", "orders", ...) and implement
    get_queryset() filtered on self.store. HasStorePermission also blocks suspended
    and unpaid stores and deactivated users on every request.
    """

    permission_classes = [IsAuthenticated, HasStorePermission]
    permission_resource: str | None = None
    permission_action: str | None = None

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.store = request.store


class PlatformAdminMixin:
    """Views only the platform (super) admin may call."""

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

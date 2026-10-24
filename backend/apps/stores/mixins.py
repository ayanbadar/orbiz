from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated

from apps.stores.permissions import IsStoreMember
from apps.stores.views import resolve_request_store


class StoreScopedMixin:
    """
    Resolve the caller's default store onto the view before queryset work.

    Subclasses must implement get_queryset() scoped to self.store.
    Missing workspace → 404 so onboarding can redirect.
    """

    permission_classes = [IsAuthenticated, IsStoreMember]
    missing_store_message = "Create a store workspace before continuing."

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        store = resolve_request_store(request)
        if store is None:
            raise NotFound(self.missing_store_message)
        self.store = store

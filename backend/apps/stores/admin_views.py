"""Platform-admin view of stores. Every view requires IsPlatformAdmin."""

from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import StandardPagination
from apps.stores.admin_serializers import AdminStoreSerializer, AdminStoreUpdateSerializer
from apps.stores.mixins import PlatformAdminMixin
from apps.stores.models import Store, StoreMembership
from apps.stores.services import delete_store, set_store_suspended

TAGS = ["platform admin: stores"]


def stores_queryset():
    admins = Prefetch(
        "memberships",
        queryset=StoreMembership.objects.filter(is_store_admin=True).select_related("user"),
        to_attr="admins",
    )
    return (
        Store.objects.select_related("subscription")
        .prefetch_related(admins)
        .annotate(user_count=Count("memberships", distinct=True))
        .order_by("-created_at")
    )


class AdminStoreListView(PlatformAdminMixin, generics.ListAPIView):
    serializer_class = AdminStoreSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = stores_queryset()
        status_filter = self.request.query_params.get("status")
        if status_filter in Store.Status.values:
            qs = qs.filter(status=status_filter)
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(memberships__user__email__icontains=search)).distinct()
        return qs

    @extend_schema(tags=TAGS, summary="List all stores", responses=AdminStoreSerializer(many=True))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AdminStoreDetailView(PlatformAdminMixin, APIView):
    def get_store(self, pk: int) -> Store:
        return get_object_or_404(stores_queryset(), pk=pk)

    @extend_schema(tags=TAGS, summary="Get a store", responses=AdminStoreSerializer)
    def get(self, request, pk: int):
        return Response(AdminStoreSerializer(self.get_store(pk)).data)

    @extend_schema(
        tags=TAGS,
        summary="Rename, suspend or reactivate a store",
        request=AdminStoreUpdateSerializer,
        responses=AdminStoreSerializer,
    )
    def patch(self, request, pk: int):
        store = self.get_store(pk)
        serializer = AdminStoreUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if "name" in data:
            store.name = data["name"]
            store.save(update_fields=["name", "updated_at"])
        if "suspended" in data:
            set_store_suspended(store, data["suspended"])
        return Response(AdminStoreSerializer(self.get_store(pk)).data)

    @extend_schema(tags=TAGS, summary="Delete a store and all its users", responses={204: None})
    def delete(self, request, pk: int):
        delete_store(self.get_store(pk))
        return Response(status=status.HTTP_204_NO_CONTENT)

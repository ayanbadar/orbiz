"""Platform-admin view of user accounts across all stores. Every view requires IsPlatformAdmin."""

from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.serializers import AdminUserUpdateSerializer
from apps.common.pagination import StandardPagination
from apps.stores.mixins import PlatformAdminMixin
from apps.stores.services import delete_store, set_user_active
from apps.stores.team_serializers import MemberSerializer

TAGS = ["platform admin: users"]


def members_queryset():
    """Every store user (never platform admins)."""
    return (
        User.objects.filter(is_superuser=False, membership__isnull=False)
        .select_related("membership__store", "membership__role")
        .order_by("-date_joined")
    )


class AdminUserListView(PlatformAdminMixin, generics.ListAPIView):
    serializer_class = MemberSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = members_queryset()
        params = self.request.query_params
        if params.get("store"):
            qs = qs.filter(membership__store_id=params["store"])
        if params.get("is_active") in ("true", "false"):
            qs = qs.filter(is_active=(params["is_active"] == "true"))
        search = params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(email__icontains=search) | Q(first_name__icontains=search) | Q(last_name__icontains=search)
            )
        return qs

    @extend_schema(tags=TAGS, summary="All users across all stores", responses=MemberSerializer(many=True))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AdminUserDetailView(PlatformAdminMixin, APIView):
    def get_user(self, pk: int) -> User:
        return get_object_or_404(members_queryset(), pk=pk)

    @extend_schema(
        tags=TAGS,
        summary="Update, deactivate or reactivate a user (a store admin's state drives their store)",
        request=AdminUserUpdateSerializer,
        responses=MemberSerializer,
    )
    def patch(self, request, pk: int):
        user = self.get_user(pk)
        serializer = AdminUserUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        fields = [f for f in ("first_name", "last_name") if f in data]
        for field in fields:
            setattr(user, field, data[field])
        if fields:
            user.save(update_fields=fields)
        if "is_active" in data and data["is_active"] != user.is_active:
            set_user_active(user, data["is_active"])
        return Response(MemberSerializer(self.get_user(pk)).data)

    @extend_schema(
        tags=TAGS,
        summary="Delete a user (a store admin takes the whole store with them)",
        responses={204: None},
    )
    def delete(self, request, pk: int):
        user = self.get_user(pk)
        if user.membership.is_store_admin:
            delete_store(user.membership.store)
        else:
            user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

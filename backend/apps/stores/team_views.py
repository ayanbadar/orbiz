from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.common.exceptions import ConflictError, ForbiddenError
from apps.common.pagination import StandardPagination
from apps.stores.mixins import StoreScopedMixin
from apps.stores.models import Role
from apps.stores.permission_codes import permission_catalog
from apps.stores.services import can_assign_role, set_user_active
from apps.stores.team_serializers import (
    MemberSerializer,
    MemberUpdateSerializer,
    RoleSerializer,
)

TAGS = ["team"]


class TeamMixin(StoreScopedMixin):
    permission_resource = "users"

    def get_role_for_assignment(self, role_id: int) -> Role:
        role = get_object_or_404(Role, pk=role_id, store=self.store)
        if not can_assign_role(self.request.membership, role):
            raise ForbiddenError("You can't assign a role with more access than your own.", code="role_too_powerful")
        return role


# --- Users ---------------------------------------------------------------


class TeamUserListView(TeamMixin, generics.ListAPIView):
    serializer_class = MemberSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = (
            User.objects.filter(membership__store=self.store)
            .select_related("membership__store", "membership__role")
            .order_by("-membership__is_store_admin", "first_name", "email")
        )
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(email__icontains=search) | Q(first_name__icontains=search) | Q(last_name__icontains=search)
            )
        is_active = self.request.query_params.get("is_active")
        if is_active in ("true", "false"):
            qs = qs.filter(is_active=(is_active == "true"))
        return qs

    @extend_schema(tags=TAGS, summary="List team members", responses=MemberSerializer(many=True))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class TeamUserDetailView(TeamMixin, APIView):
    def get_target(self, pk: int) -> User:
        target = get_object_or_404(
            User.objects.select_related("membership__store", "membership__role"),
            pk=pk,
            membership__store=self.store,
        )
        if target.pk == self.request.user.pk:
            raise ForbiddenError("You can't change your own account here.", code="self_action")
        if target.membership.is_store_admin:
            raise ForbiddenError("The store admin can't be changed here.", code="admin_protected")
        return target

    @extend_schema(
        tags=TAGS,
        summary="Update a team member (name, role, active)",
        request=MemberUpdateSerializer,
        responses=MemberSerializer,
    )
    def patch(self, request, pk: int):
        target = self.get_target(pk)
        serializer = MemberUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        update_fields = [f for f in ("first_name", "last_name") if f in data]
        for field in update_fields:
            setattr(target, field, data[field])
        if update_fields:
            target.save(update_fields=update_fields)
        if "role_id" in data:
            target.membership.role = self.get_role_for_assignment(data["role_id"])
            target.membership.save(update_fields=["role"])
        if "is_active" in data and data["is_active"] != target.is_active:
            set_user_active(target, data["is_active"])
        target.refresh_from_db()
        return Response(MemberSerializer(target).data)

    @extend_schema(tags=TAGS, summary="Delete a team member", responses={204: None})
    def delete(self, request, pk: int):
        self.get_target(pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Roles (read: users.read, write: store admin only) --------------------


class RoleMixin(TeamMixin):
    @property
    def permission_resource(self):  # type: ignore[override]
        # None means "store admin only" in HasStorePermission.
        return "users" if self.request.method in ("GET", "HEAD", "OPTIONS") else None

    def get_queryset(self):
        return Role.objects.filter(store=self.store).annotate(member_count=Count("memberships"))

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "store": self.store}


class RoleListCreateView(RoleMixin, generics.ListCreateAPIView):
    serializer_class = RoleSerializer
    pagination_class = None

    @extend_schema(tags=TAGS, summary="List roles", responses=RoleSerializer(many=True))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=TAGS, summary="Create a role", request=RoleSerializer, responses={201: RoleSerializer})
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(store=self.store)


class RoleDetailView(RoleMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = RoleSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    @extend_schema(tags=TAGS, summary="Get a role", responses=RoleSerializer)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=TAGS, summary="Update a role", request=RoleSerializer, responses=RoleSerializer)
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(tags=TAGS, summary="Delete a role (must be unassigned)", responses={204: None})
    def delete(self, request, *args, **kwargs):
        role = self.get_object()
        in_use = role.memberships.count()
        if in_use:
            raise ConflictError(
                f"{in_use} team member(s) still have this role. Reassign them first.",
                code="role_in_use",
            )
        role.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PermissionCatalogView(TeamMixin, APIView):
    @extend_schema(tags=TAGS, summary="Available permissions", responses={200: dict})
    def get(self, request):
        return Response(permission_catalog())

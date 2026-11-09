from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers import AuthTokenResponseSerializer, UserSerializer
from apps.accounts.services import issue_tokens
from apps.accounts.views import PublicAPIView
from apps.invitations.models import Invitation
from apps.invitations.serializers import (
    AcceptInvitationSerializer,
    InvitationPreviewSerializer,
    InvitationSerializer,
    InviteStaffSerializer,
    InviteStoreAdminSerializer,
)
from apps.invitations.services import (
    accept_invitation,
    create_invitation,
    get_pending_invitation,
    pending_invitations,
)
from apps.stores.mixins import PlatformAdminMixin, StoreScopedMixin
from apps.stores.models import Role
from apps.stores.services import can_assign_role
from apps.common.exceptions import ForbiddenError

TAGS = ["invitations"]


# --- Staff invitations: a store's own team (permission: users.*) -----------


class StaffInvitationMixin(StoreScopedMixin):
    permission_resource = "users"

    def get_queryset(self):
        return pending_invitations().filter(store=self.store, kind=Invitation.Kind.STAFF).select_related("role")


class StaffInvitationListCreateView(StaffInvitationMixin, generics.ListAPIView):
    serializer_class = InvitationSerializer
    pagination_class = None  # pending invites are a short list

    @extend_schema(tags=TAGS, summary="List my store's pending invitations", responses=InvitationSerializer(many=True))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=TAGS,
        summary="Invite a team member to my store",
        request=InviteStaffSerializer,
        responses={201: InvitationSerializer},
    )
    def post(self, request):
        serializer = InviteStaffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = get_object_or_404(Role, pk=serializer.validated_data["role_id"], store=self.store)
        if not can_assign_role(request.membership, role):
            raise ForbiddenError("You can't assign a role with more access than your own.", code="role_too_powerful")
        invitation = create_invitation(
            invited_by=request.user,
            email=serializer.validated_data["email"],
            kind=Invitation.Kind.STAFF,
            store=self.store,
            role=role,
        )
        return Response(InvitationSerializer(invitation).data, status=status.HTTP_201_CREATED)


class StaffInvitationDetailView(StaffInvitationMixin, APIView):
    @extend_schema(tags=TAGS, summary="Revoke a pending invitation", responses={204: None})
    def delete(self, request, pk: int):
        get_object_or_404(self.get_queryset(), pk=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Store-admin invitations: platform admin only -------------------------


class StoreAdminInvitationMixin(PlatformAdminMixin):
    def get_queryset(self):
        return pending_invitations().filter(kind=Invitation.Kind.STORE_ADMIN)


class StoreAdminInvitationListCreateView(StoreAdminInvitationMixin, generics.ListAPIView):
    serializer_class = InvitationSerializer
    pagination_class = None

    @extend_schema(tags=TAGS, summary="List pending store-admin invitations", responses=InvitationSerializer(many=True))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=TAGS,
        summary="Invite a store admin (their store is created when they accept)",
        request=InviteStoreAdminSerializer,
        responses={201: InvitationSerializer},
    )
    def post(self, request):
        serializer = InviteStoreAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invitation = create_invitation(
            invited_by=request.user,
            email=serializer.validated_data["email"],
            kind=Invitation.Kind.STORE_ADMIN,
            store_name=serializer.validated_data["store_name"],
        )
        return Response(InvitationSerializer(invitation).data, status=status.HTTP_201_CREATED)


class StoreAdminInvitationDetailView(StoreAdminInvitationMixin, APIView):
    @extend_schema(tags=TAGS, summary="Revoke a store-admin invitation", responses={204: None})
    def delete(self, request, pk: int):
        get_object_or_404(self.get_queryset(), pk=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Public: the invitee ----------------------------------------------------


class InvitationPreviewView(PublicAPIView):
    throttle_scope = "auth"

    @extend_schema(tags=TAGS, summary="Look up an invitation", responses=InvitationPreviewSerializer, auth=[])
    def get(self, request, token: str):
        invitation = get_pending_invitation(token)
        return Response(
            {
                "email": invitation.email,
                "kind": invitation.kind,
                "store_name": invitation.store.name if invitation.store else invitation.store_name,
                "role_name": invitation.role.name if invitation.role else None,
            }
        )


class InvitationAcceptView(PublicAPIView):
    throttle_scope = "auth"

    @extend_schema(
        tags=TAGS,
        summary="Accept an invitation and create the account",
        request=AcceptInvitationSerializer,
        responses={201: AuthTokenResponseSerializer},
        auth=[],
    )
    def post(self, request, token: str):
        serializer = AcceptInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = accept_invitation(
            token=token,
            first_name=serializer.validated_data["first_name"],
            last_name=serializer.validated_data["last_name"].strip(),
            password=serializer.validated_data["password"],
        )
        return Response(
            {**issue_tokens(user), "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )

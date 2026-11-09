from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.invitations.models import Invitation


class InvitationSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="role.name", read_only=True, default=None)
    invite_url = serializers.SerializerMethodField()

    class Meta:
        model = Invitation
        fields = ["id", "email", "kind", "role_name", "store_name", "expires_at", "created_at", "invite_url"]
        read_only_fields = fields

    def get_invite_url(self, invitation: Invitation) -> str | None:
        # Dev convenience: the console email backend is the only "inbox" locally.
        if not settings.DEBUG:
            return None
        from apps.invitations.services import invitation_url

        return invitation_url(invitation)


class InviteStaffSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role_id = serializers.IntegerField()

    def validate_email(self, value: str) -> str:
        return value.strip().lower()


class InviteStoreAdminSerializer(serializers.Serializer):
    email = serializers.EmailField()
    store_name = serializers.CharField(max_length=120)

    def validate_email(self, value: str) -> str:
        return value.strip().lower()

    def validate_store_name(self, value: str) -> str:
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Enter a store name.")
        return name


class InvitationPreviewSerializer(serializers.Serializer):
    email = serializers.EmailField()
    kind = serializers.CharField()
    store_name = serializers.CharField()
    role_name = serializers.CharField(allow_null=True)


class AcceptInvitationSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_first_name(self, value: str) -> str:
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Enter your first name.")
        return name

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        try:
            validate_password(attrs["password"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

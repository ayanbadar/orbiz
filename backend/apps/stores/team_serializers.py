from rest_framework import serializers

from apps.accounts.models import User
from apps.stores.models import Role
from apps.stores.permission_codes import is_valid_permission


class RoleSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ["id", "name", "description", "permissions", "member_count", "created_at"]
        read_only_fields = ["id", "member_count", "created_at"]

    def get_member_count(self, role: Role) -> int:
        return getattr(role, "member_count", 0)

    def validate_name(self, value: str) -> str:
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Enter a role name.")
        store = self.context["store"]
        clash = Role.objects.filter(store=store, name__iexact=name)
        if self.instance:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError("A role with this name already exists.")
        return name

    def validate_permissions(self, value: list[str]) -> list[str]:
        unknown = [code for code in value if not is_valid_permission(code)]
        if unknown:
            raise serializers.ValidationError(f"Unknown permissions: {', '.join(unknown)}")
        return sorted(set(value))


class MemberSerializer(serializers.ModelSerializer):
    """A user plus where they sit in a store. Used by the team page and the super admin."""

    is_store_admin = serializers.BooleanField(source="membership.is_store_admin", read_only=True)
    role = serializers.SerializerMethodField()
    store = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_store_admin",
            "role",
            "store",
            "date_joined",
            "last_login",
        ]
        read_only_fields = fields

    def get_role(self, user: User) -> dict | None:
        role = user.membership.role
        return {"id": role.pk, "name": role.name} if role else None

    def get_store(self, user: User) -> dict:
        return {
            "id": user.membership.store_id,
            "name": user.membership.store.name,
            "status": user.membership.store.status,
        }


class MemberUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
    role_id = serializers.IntegerField(required=False)

    def validate_first_name(self, value: str) -> str:
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Enter a first name.")
        return name

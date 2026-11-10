from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rest_framework import serializers

from apps.stores.models import Store, StoreMembership
from apps.stores.services import create_store_for_user


class StoreSerializer(serializers.ModelSerializer):
    """The caller's store plus what the caller may do in it (drives the UI)."""

    is_store_admin = serializers.SerializerMethodField()
    role_name = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Store
        fields = [
            "id",
            "name",
            "currency",
            "timezone",
            "business_type",
            "status",
            "is_store_admin",
            "role_name",
            "permissions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def _membership(self, store: Store) -> StoreMembership | None:
        user = self.context["request"].user
        return StoreMembership.objects.select_related("role").filter(store=store, user=user).first()

    def get_is_store_admin(self, store: Store) -> bool:
        membership = self._membership(store)
        return bool(membership and membership.is_store_admin)

    def get_role_name(self, store: Store) -> str | None:
        membership = self._membership(store)
        return membership.role.name if membership and membership.role else None

    def get_permissions(self, store: Store) -> list[str]:
        membership = self._membership(store)
        return membership.permission_codes() if membership else []


def _validate_timezone(value: str) -> str:
    """Accept only real IANA timezone names (e.g. Asia/Karachi)."""
    timezone = value.strip()
    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise serializers.ValidationError("Select a valid timezone (e.g. Asia/Karachi).")
    return timezone


class StoreCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    currency = serializers.CharField(max_length=3, default="USD")
    timezone = serializers.CharField(max_length=64, default="UTC")
    business_type = serializers.ChoiceField(
        choices=Store.BusinessType.choices,
        default=Store.BusinessType.SOCIAL,
    )

    def validate_name(self, value: str) -> str:
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Enter a store name.")
        return name

    def validate_currency(self, value: str) -> str:
        currency = value.strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise serializers.ValidationError("Use a 3-letter currency code (e.g. USD).")
        return currency

    def validate_timezone(self, value: str) -> str:
        return _validate_timezone(value)

    def create(self, validated_data):
        return create_store_for_user(user=self.context["request"].user, **validated_data)


class StoreUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ["name", "currency", "timezone", "business_type"]

    def validate_name(self, value: str) -> str:
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Enter a store name.")
        return name

    def validate_currency(self, value: str) -> str:
        currency = value.strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise serializers.ValidationError("Use a 3-letter currency code (e.g. USD).")
        return currency

    def validate_timezone(self, value: str) -> str:
        return _validate_timezone(value)

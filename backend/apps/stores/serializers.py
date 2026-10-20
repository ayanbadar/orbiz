from rest_framework import serializers

from apps.stores.models import Store, StoreMembership
from apps.stores.services import create_store_for_user, set_default_store


class StoreSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    is_default = serializers.SerializerMethodField()

    class Meta:
        model = Store
        fields = [
            "id",
            "name",
            "currency",
            "timezone",
            "business_type",
            "role",
            "is_default",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "role", "is_default", "created_at", "updated_at"]

    def _membership(self, store: Store) -> StoreMembership | None:
        user = self.context["request"].user
        return StoreMembership.objects.filter(store=store, user=user).first()

    def get_role(self, store: Store) -> str | None:
        membership = self._membership(store)
        return membership.role if membership else None

    def get_is_default(self, store: Store) -> bool:
        membership = self._membership(store)
        return bool(membership and membership.is_default)


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
        timezone = value.strip()
        if not timezone:
            raise serializers.ValidationError("Enter a timezone.")
        return timezone

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


class SetDefaultStoreSerializer(serializers.Serializer):
    store_id = serializers.IntegerField()

    def validate_store_id(self, value: int) -> int:
        user = self.context["request"].user
        if not StoreMembership.objects.filter(user=user, store_id=value).exists():
            raise serializers.ValidationError("You are not a member of that store.")
        return value

    def save(self, **kwargs):
        store = Store.objects.get(pk=self.validated_data["store_id"])
        set_default_store(user=self.context["request"].user, store=store)
        return store

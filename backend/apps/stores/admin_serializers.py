from rest_framework import serializers

from apps.stores.models import Store


class AdminStoreSerializer(serializers.ModelSerializer):
    """A store as the platform admin sees it: its admin, plan and headcount."""

    admin_email = serializers.SerializerMethodField()
    admin_name = serializers.SerializerMethodField()
    admin_is_active = serializers.SerializerMethodField()
    user_count = serializers.IntegerField(read_only=True)
    subscription_status = serializers.SerializerMethodField()
    current_period_end = serializers.SerializerMethodField()

    class Meta:
        model = Store
        fields = [
            "id",
            "name",
            "status",
            "admin_email",
            "admin_name",
            "admin_is_active",
            "user_count",
            "subscription_status",
            "current_period_end",
            "created_at",
        ]
        read_only_fields = fields

    def _admin(self, store: Store):
        # `admins` is prefetched by the view; falls back to a query for single objects.
        admins = getattr(store, "admins", None)
        if admins is None:
            admins = list(store.memberships.filter(is_store_admin=True).select_related("user"))
        return admins[0].user if admins else None

    def get_admin_email(self, store: Store) -> str | None:
        admin = self._admin(store)
        return admin.email if admin else None

    def get_admin_name(self, store: Store) -> str | None:
        admin = self._admin(store)
        return f"{admin.first_name} {admin.last_name}".strip() if admin else None

    def get_admin_is_active(self, store: Store) -> bool | None:
        admin = self._admin(store)
        return admin.is_active if admin else None

    def get_subscription_status(self, store: Store) -> str | None:
        subscription = getattr(store, "subscription", None)
        return subscription.status if subscription else None

    def get_current_period_end(self, store: Store):
        subscription = getattr(store, "subscription", None)
        return subscription.current_period_end if subscription else None


class AdminStoreUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, required=False)
    suspended = serializers.BooleanField(required=False)

    def validate_name(self, value: str) -> str:
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Enter a store name.")
        return name

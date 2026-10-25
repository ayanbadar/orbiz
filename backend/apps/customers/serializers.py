from rest_framework import serializers

from apps.common.serializers import require_nonempty_name
from apps.customers.models import Customer
from apps.customers.services import create_customer, update_customer


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CustomerCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["name", "email", "phone", "notes"]

    def validate_name(self, value: str) -> str:
        return require_nonempty_name(value, message="Enter a customer name.")

    def create(self, validated_data):
        store = self.context["store"]
        return create_customer(store=store, **validated_data)


class CustomerUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["name", "email", "phone", "notes"]

    def validate_name(self, value: str) -> str:
        return require_nonempty_name(value, message="Enter a customer name.")

    def update(self, instance, validated_data):
        return update_customer(customer=instance, **validated_data)

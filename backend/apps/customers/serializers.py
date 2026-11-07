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


class CustomerSummarySerializer(CustomerSerializer):
    """Customer plus order stats; needs the annotated customers queryset."""

    order_count = serializers.IntegerField(read_only=True)
    # Orders not yet completed or cancelled — flags who still needs a seller's attention.
    open_order_count = serializers.IntegerField(read_only=True)
    last_order_at = serializers.DateTimeField(read_only=True, allow_null=True)

    class Meta(CustomerSerializer.Meta):
        fields = [
            *CustomerSerializer.Meta.fields,
            "order_count",
            "open_order_count",
            "last_order_at",
        ]


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

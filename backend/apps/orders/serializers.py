from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.customers.models import Customer
from apps.customers.serializers import CustomerSerializer
from apps.orders.models import Order, OrderEvent, OrderLine
from apps.orders.services import create_draft, transition_fulfilment, update_draft


class OrderLineSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source="product.id", read_only=True)

    class Meta:
        model = OrderLine
        fields = [
            "id",
            "product_id",
            "product_name",
            "sku",
            "unit_price",
            "quantity",
            "line_total",
        ]


class OrderEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderEvent
        fields = [
            "id",
            "event_type",
            "from_value",
            "to_value",
            "message",
            "actor",
            "created_at",
        ]


class OrderLineInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)


class OrderSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    lines = OrderLineSerializer(many=True, read_only=True)
    events = OrderEventSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "number",
            "customer",
            "fulfilment_status",
            "payment_status",
            "currency",
            "subtotal",
            "total",
            "delivery_notes",
            "internal_notes",
            "source_message",
            "stock_deducted",
            "confirmed_at",
            "cancelled_at",
            "lines",
            "events",
            "created_at",
            "updated_at",
        ]


class OrderListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "number",
            "customer_name",
            "fulfilment_status",
            "payment_status",
            "currency",
            "total",
            "created_at",
            "updated_at",
        ]


class OrderCreateSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField(min_value=1)
    delivery_notes = serializers.CharField(required=False, allow_blank=True, default="")
    internal_notes = serializers.CharField(required=False, allow_blank=True, default="")
    source_message = serializers.CharField(required=False, allow_blank=True, default="")
    lines = OrderLineInputSerializer(many=True)

    def validate_lines(self, lines):
        if not lines:
            raise serializers.ValidationError("Add at least one line.")
        return lines

    def create(self, validated_data):
        store = self.context["store"]
        user = self.context["request"].user
        try:
            customer = Customer.objects.get(pk=validated_data["customer_id"], store=store)
        except Customer.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"customer_id": "Customer was not found in this store."}
            ) from exc
        try:
            return create_draft(
                store=store,
                user=user,
                customer=customer,
                lines=validated_data["lines"],
                delivery_notes=validated_data.get("delivery_notes", ""),
                internal_notes=validated_data.get("internal_notes", ""),
                source_message=validated_data.get("source_message", ""),
            )
        except DjangoValidationError as exc:
            if hasattr(exc, "message_dict"):
                raise serializers.ValidationError(exc.message_dict) from exc
            raise serializers.ValidationError(list(exc.messages)) from exc


class OrderUpdateSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField(min_value=1, required=False)
    delivery_notes = serializers.CharField(required=False, allow_blank=True)
    internal_notes = serializers.CharField(required=False, allow_blank=True)
    source_message = serializers.CharField(required=False, allow_blank=True)
    lines = OrderLineInputSerializer(many=True, required=False)

    def update(self, instance, validated_data):
        store = self.context["store"]
        user = self.context["request"].user
        customer = None
        if "customer_id" in validated_data:
            try:
                customer = Customer.objects.get(
                    pk=validated_data["customer_id"], store=store
                )
            except Customer.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {"customer_id": "Customer was not found in this store."}
                ) from exc
        try:
            return update_draft(
                order=instance,
                user=user,
                customer=customer,
                lines=validated_data.get("lines"),
                delivery_notes=validated_data.get("delivery_notes"),
                internal_notes=validated_data.get("internal_notes"),
                source_message=validated_data.get("source_message"),
            )
        except DjangoValidationError as exc:
            if hasattr(exc, "message_dict"):
                raise serializers.ValidationError(exc.message_dict) from exc
            raise serializers.ValidationError(list(exc.messages)) from exc


class OrderTransitionSerializer(serializers.Serializer):
    fulfilment_status = serializers.ChoiceField(
        choices=[
            Order.FulfilmentStatus.PROCESSING,
            Order.FulfilmentStatus.SHIPPED,
            Order.FulfilmentStatus.COMPLETED,
        ]
    )
    allow_unpaid = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Explicit override (e.g. COD). Default requires payment_status=paid.",
    )

    def save(self, **kwargs):
        order = self.context["order"]
        user = self.context["request"].user
        return transition_fulfilment(
            order=order,
            user=user,
            fulfilment_status=self.validated_data["fulfilment_status"],
            allow_unpaid=self.validated_data.get("allow_unpaid", False),
        )


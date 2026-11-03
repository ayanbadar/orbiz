from rest_framework import serializers

from apps.payments.models import PaymentCheckout
from apps.payments import paypal as paypal_client


class PaymentCheckoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentCheckout
        fields = [
            "id",
            "order",
            "paypal_order_id",
            "status",
            "approve_url",
            "capture_id",
            "amount",
            "currency",
            "is_sandbox",
            "last_error",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class PaymentCheckoutSummarySerializer(serializers.ModelSerializer):
    """Nested on order detail — omit heavy fields."""

    class Meta:
        model = PaymentCheckout
        fields = [
            "id",
            "paypal_order_id",
            "status",
            "approve_url",
            "capture_id",
            "amount",
            "currency",
            "is_sandbox",
            "last_error",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class PayPalConfiguredSerializer(serializers.Serializer):
    paypal_configured = serializers.BooleanField()
    paypal_sandbox = serializers.BooleanField()


def paypal_status_flags() -> dict:
    return {
        "paypal_configured": paypal_client.is_configured(),
        "paypal_sandbox": paypal_client.is_sandbox_mode(),
    }

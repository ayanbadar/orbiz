from decimal import Decimal

from rest_framework import serializers

from apps.payments.models import PaymentCheckout, PaymentInvoice, PaymentRefund
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


class PaymentRefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentRefund
        fields = [
            "id",
            "paypal_refund_id",
            "status",
            "source",
            "amount",
            "currency",
            "note_to_payer",
            "last_error",
            "created_at",
        ]
        read_only_fields = fields


class PaymentInvoiceSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentInvoice
        fields = [
            "id",
            "paypal_invoice_id",
            "invoice_number",
            "status",
            "recipient_email",
            "recipient_view_url",
            "amount",
            "currency",
            "is_sandbox",
            "last_error",
            "sent_at",
            "paid_at",
            "created_at",
        ]
        read_only_fields = fields


class RefundRequestSerializer(serializers.Serializer):
    """Omit `amount` to refund everything that is still refundable."""

    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
    )
    note_to_payer = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
    )


class InvoiceRequestSerializer(serializers.Serializer):
    """Leave `recipient_email` blank for a link-only invoice (nothing is emailed)."""

    recipient_email = serializers.EmailField(
        required=False,
        allow_blank=True,
        default="",
    )


class PayPalConfiguredSerializer(serializers.Serializer):
    paypal_configured = serializers.BooleanField()
    paypal_sandbox = serializers.BooleanField()


class PaymentCheckoutDetailSerializer(PayPalConfiguredSerializer):
    checkout = PaymentCheckoutSerializer(allow_null=True, read_only=True)


def paypal_status_flags() -> dict:
    return {
        "paypal_configured": paypal_client.is_configured(),
        "paypal_sandbox": paypal_client.is_sandbox_mode(),
    }

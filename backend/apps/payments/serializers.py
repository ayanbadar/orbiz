from decimal import Decimal

from rest_framework import serializers

from apps.payments.models import PaymentCheckout, PaymentInvoice, PaymentRefund
from apps.payments import emails as payment_emails
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
            "delivered_via",
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


class PaymentRequestSummarySerializer(serializers.Serializer):
    """The one open PayPal payment request on an order, as the seller's UI renders it."""

    kind = serializers.ChoiceField(choices=["invoice", "checkout", "none"])
    status = serializers.CharField(allow_blank=True)
    url = serializers.CharField(allow_blank=True)
    recipient_email = serializers.CharField(allow_blank=True)
    delivered_via = serializers.CharField(allow_blank=True)
    last_emailed_at = serializers.DateTimeField(allow_null=True)
    last_email_status = serializers.CharField(allow_blank=True)
    last_email_error = serializers.CharField(allow_blank=True)
    can_email = serializers.BooleanField()
    delivery_mode = serializers.ChoiceField(choices=["orbiz", "paypal"])


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


class EmailLinkRequestSerializer(serializers.Serializer):
    """Leave `recipient_email` blank to use the customer's email on file."""

    recipient_email = serializers.EmailField(
        required=False,
        allow_blank=True,
        default="",
    )
    kind = serializers.ChoiceField(
        choices=[payment_emails.REQUEST, payment_emails.REMINDER],
        required=False,
        default=payment_emails.REQUEST,
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

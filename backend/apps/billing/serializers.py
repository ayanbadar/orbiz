from rest_framework import serializers

from apps.billing.models import Payment, Subscription


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "amount_cents", "status", "reference", "created_at"]
        read_only_fields = fields


class BillingSerializer(serializers.Serializer):
    plan_price_cents = serializers.IntegerField()
    plan_period_days = serializers.IntegerField()
    store_status = serializers.CharField()
    subscription_status = serializers.CharField()
    current_period_end = serializers.DateTimeField(allow_null=True)
    payments = PaymentSerializer(many=True)


class CheckoutSerializer(serializers.Serializer):
    """Mock checkout: card details are accepted for realism and discarded."""

    card_number = serializers.CharField(required=False, allow_blank=True, write_only=True)
    simulate_failure = serializers.BooleanField(required=False, default=False)


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ["status", "amount_cents", "current_period_end"]
        read_only_fields = fields

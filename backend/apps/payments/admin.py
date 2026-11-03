from django.contrib import admin

from apps.payments.models import PaymentCheckout, PayPalWebhookEvent


@admin.register(PaymentCheckout)
class PaymentCheckoutAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "paypal_order_id",
        "status",
        "amount",
        "currency",
        "is_sandbox",
        "created_at",
    )
    list_filter = ("status", "is_sandbox", "currency")
    search_fields = ("paypal_order_id", "capture_id", "order__number")
    raw_id_fields = ("order",)


@admin.register(PayPalWebhookEvent)
class PayPalWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("id", "event_id", "event_type", "order", "received_at", "processed_at")
    list_filter = ("event_type",)
    search_fields = ("event_id", "event_type")
    raw_id_fields = ("order",)

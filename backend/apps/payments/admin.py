from django.contrib import admin

from apps.payments.models import (
    PaymentCheckout,
    PaymentInvoice,
    PaymentRefund,
    PayPalWebhookEvent,
)


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


@admin.register(PaymentRefund)
class PaymentRefundAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "paypal_refund_id",
        "status",
        "source",
        "amount",
        "currency",
        "created_at",
    )
    list_filter = ("status", "source", "currency")
    search_fields = ("paypal_refund_id", "capture_id", "order__number")
    raw_id_fields = ("order", "actor")


@admin.register(PaymentInvoice)
class PaymentInvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "invoice_number",
        "paypal_invoice_id",
        "status",
        "recipient_email",
        "amount",
        "currency",
        "created_at",
    )
    list_filter = ("status", "is_sandbox", "currency")
    search_fields = ("invoice_number", "paypal_invoice_id", "recipient_email", "order__number")
    raw_id_fields = ("order",)


@admin.register(PayPalWebhookEvent)
class PayPalWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("id", "event_id", "event_type", "order", "received_at", "processed_at")
    list_filter = ("event_type",)
    search_fields = ("event_id", "event_type")
    raw_id_fields = ("order",)

from django.urls import path

from apps.payments.views import (
    PaymentCheckoutCaptureView,
    PaymentCheckoutCreateView,
    PaymentCheckoutDetailView,
    PaymentInvoiceCancelView,
    PaymentInvoiceCreateView,
    PaymentLinkEmailView,
    PaymentRefundView,
    PayPalWebhookView,
)

urlpatterns = [
    path(
        "orders/<int:order_id>/checkout/",
        PaymentCheckoutCreateView.as_view(),
        name="payment-checkout-create",
    ),
    path(
        "orders/<int:order_id>/capture/",
        PaymentCheckoutCaptureView.as_view(),
        name="payment-checkout-capture",
    ),
    path(
        "orders/<int:order_id>/refund/",
        PaymentRefundView.as_view(),
        name="payment-refund-create",
    ),
    path(
        "orders/<int:order_id>/invoice/",
        PaymentInvoiceCreateView.as_view(),
        name="payment-invoice-create",
    ),
    path(
        "orders/<int:order_id>/email-link/",
        PaymentLinkEmailView.as_view(),
        name="payment-link-email",
    ),
    path(
        "orders/<int:order_id>/invoice/cancel/",
        PaymentInvoiceCancelView.as_view(),
        name="payment-invoice-cancel",
    ),
    path(
        "orders/<int:order_id>/",
        PaymentCheckoutDetailView.as_view(),
        name="payment-checkout-detail",
    ),
    path(
        "webhooks/paypal/",
        PayPalWebhookView.as_view(),
        name="payment-paypal-webhook",
    ),
]

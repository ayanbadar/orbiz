from django.urls import path

from apps.payments.views import (
    PaymentCheckoutCaptureView,
    PaymentCheckoutCreateView,
    PaymentCheckoutDetailView,
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

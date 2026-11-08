from django.urls import path

from apps.billing import views

urlpatterns = [
    path("", views.BillingView.as_view(), name="billing"),
    path("checkout/", views.CheckoutView.as_view(), name="billing-checkout"),
    path("cancel/", views.CancelView.as_view(), name="billing-cancel"),
]

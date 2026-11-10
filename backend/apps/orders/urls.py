from django.urls import path

from apps.orders.views import (
    OrderAbandonPaymentView,
    OrderCancelView,
    OrderConfirmView,
    OrderDetailView,
    OrderListCreateView,
    OrderMarkPaidView,
    OrderTransitionView,
)

urlpatterns = [
    path("", OrderListCreateView.as_view(), name="order-list-create"),
    path("<int:pk>/", OrderDetailView.as_view(), name="order-detail"),
    path("<int:pk>/confirm/", OrderConfirmView.as_view(), name="order-confirm"),
    path("<int:pk>/cancel/", OrderCancelView.as_view(), name="order-cancel"),
    path("<int:pk>/transition/", OrderTransitionView.as_view(), name="order-transition"),
    path(
        "<int:pk>/abandon-payment/",
        OrderAbandonPaymentView.as_view(),
        name="order-abandon-payment",
    ),
    path("<int:pk>/mark-paid/", OrderMarkPaidView.as_view(), name="order-mark-paid"),
]

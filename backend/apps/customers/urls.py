from django.urls import path

from apps.customers.views import CustomerDetailView, CustomerListCreateView

urlpatterns = [
    path("", CustomerListCreateView.as_view(), name="customer-list-create"),
    path("<int:pk>/", CustomerDetailView.as_view(), name="customer-detail"),
]

from django.db.models import Q
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.response import Response

from apps.customers.models import Customer
from apps.customers.serializers import (
    CustomerCreateSerializer,
    CustomerSerializer,
    CustomerUpdateSerializer,
)
from apps.stores.mixins import StoreScopedMixin


class CustomerStoreMixin(StoreScopedMixin):
    missing_store_message = "Create a store workspace before managing customers."

    def get_queryset(self):
        return Customer.objects.filter(store=self.store)


@extend_schema_view(
    get=extend_schema(tags=["customers"], summary="List customers"),
    post=extend_schema(
        tags=["customers"],
        summary="Create customer",
        request=CustomerCreateSerializer,
    ),
)
class CustomerListCreateView(CustomerStoreMixin, generics.ListCreateAPIView):
    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "writes"
            return super().get_throttles()
        return []

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CustomerCreateSerializer
        return CustomerSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["store"] = self.store
        return context

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q)
            )
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer = serializer.save()
        return Response(CustomerSerializer(customer).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(tags=["customers"], summary="Get customer"),
    patch=extend_schema(
        tags=["customers"],
        summary="Update customer",
        request=CustomerUpdateSerializer,
    ),
)
class CustomerDetailView(CustomerStoreMixin, generics.RetrieveUpdateAPIView):
    http_method_names = ["get", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return CustomerUpdateSerializer
        return CustomerSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["store"] = self.store
        return context

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        customer = serializer.save()
        return Response(CustomerSerializer(customer).data)

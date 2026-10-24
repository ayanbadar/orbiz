from django.db.models import Exists, OuterRef, Prefetch, Q
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order, OrderEvent, OrderLine
from apps.orders.serializers import (
    OrderCreateSerializer,
    OrderListSerializer,
    OrderSerializer,
    OrderTransitionSerializer,
    OrderUpdateSerializer,
)
from apps.orders.services import abandon_payment, cancel_order, confirm_order, mark_order_paid
from apps.stores.mixins import StoreScopedMixin


class OrderStoreMixin(StoreScopedMixin):
    missing_store_message = "Create a store workspace before managing orders."

    def get_queryset(self):
        return (
            Order.objects.filter(store=self.store)
            .select_related("customer")
            .prefetch_related(
                Prefetch("lines", queryset=OrderLine.objects.select_related("product")),
                Prefetch(
                    "events",
                    queryset=OrderEvent.objects.select_related("actor").order_by(
                        "-created_at"
                    ),
                ),
            )
        )


@extend_schema_view(
    get=extend_schema(tags=["orders"], summary="List orders"),
    post=extend_schema(
        tags=["orders"], summary="Create draft order", request=OrderCreateSerializer
    ),
)
class OrderListCreateView(OrderStoreMixin, generics.ListCreateAPIView):
    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "writes"
            return super().get_throttles()
        return []

    def get_serializer_class(self):
        if self.request.method == "POST":
            return OrderCreateSerializer
        return OrderListSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["store"] = self.store
        return context

    def get_queryset(self):
        # List serializer only needs customer; detail prefetch stays on the mixin.
        if self.request.method == "GET":
            qs = Order.objects.filter(store=self.store).select_related("customer")
        else:
            qs = super().get_queryset()
        qs = qs.order_by("-created_at")
        q = self.request.query_params.get("q")
        if q:
            line_match = OrderLine.objects.filter(
                order_id=OuterRef("pk"),
                sku__icontains=q,
            )
            qs = qs.filter(
                Q(number__icontains=q)
                | Q(customer__name__icontains=q)
                | Exists(line_match)
            )
        fulfilment = self.request.query_params.get("fulfilment_status")
        if fulfilment:
            qs = qs.filter(fulfilment_status=fulfilment)
        payment = self.request.query_params.get("payment_status")
        if payment:
            qs = qs.filter(payment_status=payment)
        ordering = self.request.query_params.get("ordering") or "-created_at"
        allowed = {
            "created_at",
            "-created_at",
            "total",
            "-total",
            "number",
            "-number",
            "customer__name",
            "-customer__name",
            "updated_at",
            "-updated_at",
        }
        if ordering in allowed:
            qs = qs.order_by(ordering)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        order = OrderStoreMixin.get_queryset(self).get(pk=order.pk)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(tags=["orders"], summary="Get order"),
    patch=extend_schema(
        tags=["orders"], summary="Update draft order", request=OrderUpdateSerializer
    ),
)
class OrderDetailView(OrderStoreMixin, generics.RetrieveUpdateAPIView):
    http_method_names = ["get", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return OrderUpdateSerializer
        return OrderSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["store"] = self.store
        return context

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        order = self.get_queryset().get(pk=order.pk)
        return Response(OrderSerializer(order).data)


class OrderConfirmView(OrderStoreMixin, APIView):
    throttle_scope = "writes"

    @extend_schema(
        tags=["orders"],
        summary="Confirm draft order (deduct stock)",
        request=None,
        responses={200: OrderSerializer},
    )
    def post(self, request, pk):
        order = generics.get_object_or_404(self.get_queryset(), pk=pk)
        order = confirm_order(order=order, user=request.user)
        order = self.get_queryset().get(pk=order.pk)
        return Response(OrderSerializer(order).data)


class OrderCancelView(OrderStoreMixin, APIView):
    throttle_scope = "writes"

    @extend_schema(
        tags=["orders"],
        summary="Cancel order (restore stock if deducted)",
        request=None,
        responses={200: OrderSerializer},
    )
    def post(self, request, pk):
        order = generics.get_object_or_404(self.get_queryset(), pk=pk)
        order = cancel_order(order=order, user=request.user)
        order = self.get_queryset().get(pk=order.pk)
        return Response(OrderSerializer(order).data)


class OrderTransitionView(OrderStoreMixin, APIView):
    throttle_scope = "writes"

    @extend_schema(
        tags=["orders"],
        summary="Transition fulfilment status (paid required unless allow_unpaid)",
        request=OrderTransitionSerializer,
        responses={200: OrderSerializer},
    )
    def post(self, request, pk):
        order = generics.get_object_or_404(self.get_queryset(), pk=pk)
        serializer = OrderTransitionSerializer(
            data=request.data,
            context={"order": order, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        order = self.get_queryset().get(pk=order.pk)
        return Response(OrderSerializer(order).data)


class OrderAbandonPaymentView(OrderStoreMixin, APIView):
    throttle_scope = "writes"

    @extend_schema(
        tags=["orders"],
        summary="Abandon payment attempt (order stays unfulfilled)",
        request=None,
        responses={200: OrderSerializer},
    )
    def post(self, request, pk):
        order = generics.get_object_or_404(self.get_queryset(), pk=pk)
        order = abandon_payment(order=order, user=request.user)
        order = self.get_queryset().get(pk=order.pk)
        return Response(OrderSerializer(order).data)


class OrderMarkPaidView(OrderStoreMixin, APIView):
    """Temporary until §2.7 verified PayPal webhooks own this transition."""

    throttle_scope = "writes"

    @extend_schema(
        tags=["orders"],
        summary="Mark payment paid (demo / pre-PayPal)",
        request=None,
        responses={200: OrderSerializer},
    )
    def post(self, request, pk):
        order = generics.get_object_or_404(self.get_queryset(), pk=pk)
        order = mark_order_paid(
            order=order,
            user=request.user,
            message="Payment marked paid (demo / pre-PayPal).",
        )
        order = self.get_queryset().get(pk=order.pk)
        return Response(OrderSerializer(order).data)

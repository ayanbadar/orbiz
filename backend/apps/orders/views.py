from datetime import datetime, time, timedelta

from django.db.models import Exists, OuterRef, Prefetch, Q
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.mixins import InputOutputSerializerMixin, WritesThrottleOnPostMixin
from apps.common.query_params import parse_decimal, parse_int, resolve_ordering
from apps.orders.models import Order, OrderEvent, OrderLine
from apps.orders.serializers import (
    OrderConfirmSerializer,
    OrderCreateSerializer,
    OrderListSerializer,
    OrderSerializer,
    OrderTransitionSerializer,
    OrderUpdateSerializer,
)
from apps.orders.services import abandon_payment, cancel_order, confirm_order, mark_order_paid
from apps.payments.services import notify_order_confirmed
from apps.stores.mixins import StoreScopedMixin


ORDER_ORDERINGS = frozenset(
    {
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
)


def _as_aware(value: datetime) -> datetime:
    if timezone.is_naive(value):
        return timezone.make_aware(value, timezone.get_current_timezone())
    return value


def _parse_day_start(raw: str | None) -> datetime | None:
    if not raw:
        return None
    parsed = parse_datetime(raw) or parse_date(raw)
    if parsed is None:
        return None
    if isinstance(parsed, datetime):
        return _as_aware(parsed)
    return _as_aware(datetime.combine(parsed, time.min))


def _parse_day_end_exclusive(raw: str | None) -> datetime | None:
    """End bound exclusive: next calendar day at 00:00 when given a date-only string."""
    if not raw:
        return None
    parsed_dt = parse_datetime(raw)
    if parsed_dt is not None:
        return _as_aware(parsed_dt)
    parsed_date = parse_date(raw)
    if parsed_date is None:
        return None
    return _as_aware(datetime.combine(parsed_date + timedelta(days=1), time.min))


class OrderStoreMixin(StoreScopedMixin):
    permission_resource = "orders"

    def get_queryset(self):
        return (
            Order.objects.filter(store=self.store)
            .select_related("customer")
            .prefetch_related(
                Prefetch("lines", queryset=OrderLine.objects.select_related("product")),
                Prefetch(
                    "events",
                    queryset=OrderEvent.objects.select_related("actor").order_by(
                        "-created_at",
                        "-id",
                    ),
                ),
            )
        )


@extend_schema_view(
    get=extend_schema(tags=["orders"], summary="List orders"),
    post=extend_schema(
        tags=["orders"],
        summary="Create draft order",
        request=OrderCreateSerializer,
        responses={201: OrderSerializer},
    ),
)
class OrderListCreateView(
    WritesThrottleOnPostMixin,
    InputOutputSerializerMixin,
    OrderStoreMixin,
    generics.ListCreateAPIView,
):
    serializer_class = OrderListSerializer
    input_serializer_class = OrderCreateSerializer
    output_serializer_class = OrderSerializer

    def get_queryset(self):
        # List serializer only needs customer; detail prefetch stays on the mixin
        # (POST re-reads the created order through it for the full response).
        if self.request.method == "GET":
            return Order.objects.filter(store=self.store).select_related("customer")
        return super().get_queryset()

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)
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
        number = self.request.query_params.get("number")
        if number:
            qs = qs.filter(number__icontains=number)
        customer_name = self.request.query_params.get("customer_name")
        if customer_name:
            qs = qs.filter(customer__name__icontains=customer_name)
        customer_id = parse_int(self.request.query_params.get("customer_id"))
        if customer_id is not None:
            qs = qs.filter(customer_id=customer_id)
        fulfilment = self.request.query_params.get("fulfilment_status")
        if fulfilment:
            qs = qs.filter(fulfilment_status=fulfilment)
        payment = self.request.query_params.get("payment_status")
        if payment:
            qs = qs.filter(payment_status=payment)
        total_min = parse_decimal(self.request.query_params.get("total_min"))
        if total_min is not None:
            qs = qs.filter(total__gte=total_min)
        total_max = parse_decimal(self.request.query_params.get("total_max"))
        if total_max is not None:
            qs = qs.filter(total__lte=total_max)
        created_after = _parse_day_start(self.request.query_params.get("created_after"))
        if created_after is not None:
            qs = qs.filter(created_at__gte=created_after)
        created_before = _parse_day_end_exclusive(
            self.request.query_params.get("created_before")
        )
        if created_before is not None:
            qs = qs.filter(created_at__lt=created_before)
        ordering = resolve_ordering(
            self.request.query_params.get("ordering"),
            allowed=ORDER_ORDERINGS,
            default="-created_at",
        )
        return qs.order_by(ordering)


@extend_schema_view(
    get=extend_schema(tags=["orders"], summary="Get order"),
    patch=extend_schema(
        tags=["orders"],
        summary="Update draft order",
        request=OrderUpdateSerializer,
        responses={200: OrderSerializer},
    ),
)
class OrderDetailView(
    InputOutputSerializerMixin,
    OrderStoreMixin,
    generics.RetrieveUpdateAPIView,
):
    http_method_names = ["get", "patch", "head", "options"]
    serializer_class = OrderSerializer
    input_serializer_class = OrderUpdateSerializer


class OrderConfirmView(OrderStoreMixin, APIView):
    permission_action = "update"
    throttle_scope = "writes"

    @extend_schema(
        tags=["orders"],
        summary="Confirm draft order (deduct stock), optionally emailing the customer",
        request=OrderConfirmSerializer,
        responses={200: OrderSerializer},
    )
    def post(self, request, pk):
        serializer = OrderConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notify_customer = serializer.validated_data["notify_customer"]
        order = generics.get_object_or_404(self.get_queryset(), pk=pk)
        # Refuse before confirming, so nothing is half done when there is nobody to email.
        if notify_customer and not order.customer.email:
            raise ValidationError(
                {"notify_customer": "This customer has no email address on file."}
            )
        order = confirm_order(order=order, user=request.user)
        if notify_customer:
            notify_order_confirmed(order=order, user=request.user)
        order = self.get_queryset().get(pk=order.pk)
        return Response(OrderSerializer(order).data)


class OrderCancelView(OrderStoreMixin, APIView):
    permission_action = "update"
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
    permission_action = "update"
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
    permission_action = "update"
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
    permission_action = "update"
    """Temporary until §2.7 verified PayPal webhooks own this transition."""

    throttle_scope = "writes"

    @extend_schema(
        tags=["orders"],
        summary="Mark payment paid (demo / offline fallback)",
        request=None,
        responses={200: OrderSerializer},
    )
    def post(self, request, pk):
        order = generics.get_object_or_404(self.get_queryset(), pk=pk)
        order = mark_order_paid(
            order=order,
            user=request.user,
            message="Payment marked paid (demo / offline fallback).",
        )
        order = self.get_queryset().get(pk=order.pk)
        return Response(OrderSerializer(order).data)

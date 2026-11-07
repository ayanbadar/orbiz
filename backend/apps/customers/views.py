from django.db.models import Count, F, Max, Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import generics

from apps.common.mixins import InputOutputSerializerMixin, WritesThrottleOnPostMixin
from apps.common.query_params import parse_int, resolve_ordering
from apps.customers.models import Customer
from apps.customers.serializers import (
    CustomerCreateSerializer,
    CustomerSummarySerializer,
    CustomerUpdateSerializer,
)
from apps.orders.models import Order
from apps.stores.mixins import StoreScopedMixin

# Not yet completed or cancelled — mirrors the Orders page's own "open" chips,
# so "needs attention" means the same thing on both screens.
OPEN_FULFILMENT_STATUSES = (
    Order.FulfilmentStatus.DRAFT,
    Order.FulfilmentStatus.UNFULFILLED,
    Order.FulfilmentStatus.PROCESSING,
    Order.FulfilmentStatus.SHIPPED,
)

CUSTOMER_ORDERINGS = frozenset(
    {
        "name",
        "-name",
        "order_count",
        "-order_count",
        "open_order_count",
        "-open_order_count",
        "last_order_at",
        "-last_order_at",
        "created_at",
        "-created_at",
    }
)

LIST_PARAMETERS = [
    OpenApiParameter("q", OpenApiTypes.STR, description="Search name, email, or phone."),
    OpenApiParameter("name", OpenApiTypes.STR, description="Name contains."),
    OpenApiParameter("email", OpenApiTypes.STR, description="Email contains."),
    OpenApiParameter("phone", OpenApiTypes.STR, description="Phone contains."),
    OpenApiParameter("orders_min", OpenApiTypes.INT, description="At least this many orders."),
    OpenApiParameter("orders_max", OpenApiTypes.INT, description="At most this many orders."),
    OpenApiParameter(
        "needs_attention",
        OpenApiTypes.BOOL,
        description="Only customers with at least one open order (draft/unfulfilled/processing/shipped).",
    ),
    OpenApiParameter(
        "ordering",
        OpenApiTypes.STR,
        enum=sorted(CUSTOMER_ORDERINGS),
        description="Sort key; defaults to name. Customers with no orders sort last by last_order_at.",
    ),
]


def _order_by_expression(ordering: str):
    # Never-ordered customers have a NULL last_order_at; keep them at the bottom
    # in both directions (Postgres puts NULLs first on DESC by default).
    if ordering.lstrip("-") == "last_order_at":
        field = F("last_order_at")
        return field.desc(nulls_last=True) if ordering.startswith("-") else field.asc(nulls_last=True)
    return ordering


class CustomerStoreMixin(StoreScopedMixin):
    missing_store_message = "Create a store workspace before managing customers."

    def get_queryset(self):
        # Every customer response carries its order stats (one grouped query, no N+1).
        return Customer.objects.filter(store=self.store).annotate(
            order_count=Count("orders"),
            open_order_count=Count(
                "orders",
                filter=Q(orders__fulfilment_status__in=OPEN_FULFILMENT_STATUSES),
            ),
            last_order_at=Max("orders__created_at"),
        )


@extend_schema_view(
    get=extend_schema(tags=["customers"], summary="List customers", parameters=LIST_PARAMETERS),
    post=extend_schema(
        tags=["customers"],
        summary="Create customer",
        request=CustomerCreateSerializer,
        responses={201: CustomerSummarySerializer},
    ),
)
class CustomerListCreateView(
    WritesThrottleOnPostMixin,
    InputOutputSerializerMixin,
    CustomerStoreMixin,
    generics.ListCreateAPIView,
):
    serializer_class = CustomerSummarySerializer
    input_serializer_class = CustomerCreateSerializer

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)
        params = self.request.query_params
        q = params.get("q")
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q))
        for field in ("name", "email", "phone"):
            value = params.get(field)
            if value:
                qs = qs.filter(**{f"{field}__icontains": value})
        orders_min = parse_int(params.get("orders_min"))
        if orders_min is not None:
            qs = qs.filter(order_count__gte=orders_min)
        orders_max = parse_int(params.get("orders_max"))
        if orders_max is not None:
            qs = qs.filter(order_count__lte=orders_max)
        if params.get("needs_attention") == "true":
            qs = qs.filter(open_order_count__gt=0)
        ordering = resolve_ordering(params.get("ordering"), allowed=CUSTOMER_ORDERINGS, default="name")
        # id breaks ties so page boundaries stay stable for equal sort keys.
        return qs.order_by(_order_by_expression(ordering), "id")


@extend_schema_view(
    get=extend_schema(tags=["customers"], summary="Get customer"),
    patch=extend_schema(
        tags=["customers"],
        summary="Update customer",
        request=CustomerUpdateSerializer,
        responses={200: CustomerSummarySerializer},
    ),
)
class CustomerDetailView(
    InputOutputSerializerMixin,
    CustomerStoreMixin,
    generics.RetrieveUpdateAPIView,
):
    http_method_names = ["get", "patch", "head", "options"]
    serializer_class = CustomerSummarySerializer
    input_serializer_class = CustomerUpdateSerializer

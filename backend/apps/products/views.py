from django.db.models import F, Q
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.mixins import InputOutputSerializerMixin, WritesThrottleOnPostMixin
from apps.common.query_params import parse_decimal, parse_int, resolve_ordering
from apps.products.models import InventoryAdjustment, Product
from apps.orders.services import recent_usage_for_product
from apps.products.serializers import (
    AdjustStockSerializer,
    Channel3SearchResponseSerializer,
    Channel3SearchSerializer,
    CheckStockResponseSerializer,
    CheckStockSerializer,
    ImportFromChannel3Serializer,
    InventoryAdjustmentSerializer,
    ProductCreateSerializer,
    ProductOrderUsageSerializer,
    ProductSerializer,
    ProductUpdateSerializer,
)
from apps.products.services import deactivate_product
from apps.stores.mixins import StoreScopedMixin


PRODUCT_ORDERINGS = frozenset(
    {
        "name",
        "-name",
        "updated_at",
        "-updated_at",
        "stock_quantity",
        "-stock_quantity",
        "price",
        "-price",
    }
)


class ProductStoreMixin(StoreScopedMixin):
    permission_resource = "products"

    def get_queryset(self):
        return Product.objects.filter(store=self.store)


@extend_schema_view(
    get=extend_schema(tags=["products"], summary="List products"),
    post=extend_schema(
        tags=["products"],
        summary="Create product",
        request=ProductCreateSerializer,
        responses={201: ProductSerializer},
    ),
)
class ProductListCreateView(
    WritesThrottleOnPostMixin,
    InputOutputSerializerMixin,
    ProductStoreMixin,
    generics.ListCreateAPIView,
):
    serializer_class = ProductSerializer
    input_serializer_class = ProductCreateSerializer

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q))
        name = self.request.query_params.get("name")
        if name:
            qs = qs.filter(name__icontains=name)
        sku = self.request.query_params.get("sku")
        if sku:
            qs = qs.filter(sku__icontains=sku)
        is_active = self.request.query_params.get("is_active")
        if is_active in {"true", "false"}:
            qs = qs.filter(is_active=is_active == "true")
        if self.request.query_params.get("low_stock") == "true":
            qs = qs.filter(stock_quantity__lte=F("low_stock_threshold"))
        if self.request.query_params.get("out_of_stock") == "true":
            qs = qs.filter(stock_quantity=0)
        if self.request.query_params.get("in_stock") == "true":
            qs = qs.filter(
                is_active=True,
                stock_quantity__gt=F("low_stock_threshold"),
            )
        price_min = parse_decimal(self.request.query_params.get("price_min"))
        if price_min is not None:
            qs = qs.filter(price__gte=price_min)
        price_max = parse_decimal(self.request.query_params.get("price_max"))
        if price_max is not None:
            qs = qs.filter(price__lte=price_max)
        stock_min = parse_int(self.request.query_params.get("stock_min"))
        if stock_min is not None:
            qs = qs.filter(stock_quantity__gte=stock_min)
        stock_max = parse_int(self.request.query_params.get("stock_max"))
        if stock_max is not None:
            qs = qs.filter(stock_quantity__lte=stock_max)
        ordering = resolve_ordering(
            self.request.query_params.get("ordering"),
            allowed=PRODUCT_ORDERINGS,
            default="name",
        )
        return qs.order_by(ordering)


@extend_schema_view(
    get=extend_schema(tags=["products"], summary="Get product"),
    patch=extend_schema(
        tags=["products"],
        summary="Update product",
        request=ProductUpdateSerializer,
        responses={200: ProductSerializer},
    ),
    delete=extend_schema(tags=["products"], summary="Deactivate product"),
)
class ProductDetailView(
    InputOutputSerializerMixin,
    ProductStoreMixin,
    generics.RetrieveUpdateDestroyAPIView,
):
    http_method_names = ["get", "patch", "delete", "head", "options"]
    serializer_class = ProductSerializer
    input_serializer_class = ProductUpdateSerializer

    def perform_destroy(self, instance):
        deactivate_product(product=instance)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        instance.refresh_from_db()
        return Response(ProductSerializer(instance).data)


class AdjustStockView(ProductStoreMixin, APIView):
    permission_action = "update"
    throttle_scope = "writes"

    @extend_schema(
        tags=["products"],
        summary="Adjust stock",
        request=AdjustStockSerializer,
        responses=InventoryAdjustmentSerializer,
    )
    def post(self, request, pk):
        product = generics.get_object_or_404(self.get_queryset(), pk=pk)
        serializer = AdjustStockSerializer(
            data=request.data,
            context={"request": request, "product": product},
        )
        serializer.is_valid(raise_exception=True)
        adjustment = serializer.save()
        return Response(InventoryAdjustmentSerializer(adjustment).data, status=status.HTTP_201_CREATED)


class CheckStockView(ProductStoreMixin, APIView):
    permission_action = "read"
    """Product-side stock check for Orders (§2.4) to call before committing a line."""

    @extend_schema(
        tags=["products"],
        summary="Check stock availability",
        request=CheckStockSerializer,
        responses={200: CheckStockResponseSerializer},
    )
    def post(self, request, pk):
        product = generics.get_object_or_404(self.get_queryset(), pk=pk)
        serializer = CheckStockSerializer(
            data=request.data,
            context={"request": request, "product": product},
        )
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save())


class ProductAdjustmentsView(ProductStoreMixin, generics.ListAPIView):
    serializer_class = InventoryAdjustmentSerializer

    @extend_schema(tags=["products"], summary="List stock adjustments")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        product = generics.get_object_or_404(
            Product.objects.filter(store=self.store),
            pk=self.kwargs["pk"],
        )
        return InventoryAdjustment.objects.filter(product=product).select_related("created_by")


class Channel3SearchView(ProductStoreMixin, APIView):
    permission_action = "read"
    throttle_scope = "channel3"

    @extend_schema(
        tags=["products"],
        summary="Search Channel3 catalog",
        request=Channel3SearchSerializer,
        responses=Channel3SearchResponseSerializer,
    )
    def post(self, request):
        serializer = Channel3SearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        return Response(data)


class ImportFromChannel3View(ProductStoreMixin, APIView):
    permission_action = "create"
    throttle_scope = "writes"

    @extend_schema(
        tags=["products"],
        summary="Import product from Channel3",
        request=ImportFromChannel3Serializer,
        responses={201: ProductSerializer},
    )
    def post(self, request):
        serializer = ImportFromChannel3Serializer(
            data=request.data,
            context={"request": request, "store": self.store},
        )
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)


class ProductOrderUsageView(ProductStoreMixin, APIView):
    """Recent order lines for a product (product detail §2.5 hook)."""

    @extend_schema(
        tags=["products"],
        summary="Recent order usage for product",
        responses={200: ProductOrderUsageSerializer(many=True)},
    )
    def get(self, request, pk):
        product = generics.get_object_or_404(self.get_queryset(), pk=pk)
        payload = recent_usage_for_product(product=product)
        return Response(ProductOrderUsageSerializer(payload, many=True).data)

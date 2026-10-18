from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.common.exceptions import ApplicationError, BadGatewayError, ServiceUnavailableError
from apps.products.channel3 import Channel3Error, Channel3NotConfigured, retrieve_product, search_products
from apps.products.models import InventoryAdjustment, Product
from apps.products.services import (
    adjust_stock,
    create_product,
    import_product_from_channel3,
    update_product,
)


def _raise_channel3(exc: Channel3Error) -> None:
    if isinstance(exc, Channel3NotConfigured):
        raise ServiceUnavailableError(str(exc)) from exc
    if exc.status_code is None or exc.status_code >= 500:
        raise BadGatewayError(str(exc)) from exc
    if "unreachable" in str(exc).lower():
        raise BadGatewayError(str(exc)) from exc
    raise ApplicationError(str(exc)) from exc


class ProductSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "sku",
            "description",
            "price",
            "currency",
            "stock_quantity",
            "low_stock_threshold",
            "is_active",
            "is_low_stock",
            "image_url",
            "channel3_product_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "currency",
            "stock_quantity",
            "is_low_stock",
            "channel3_product_id",
            "created_at",
            "updated_at",
        ]


class ProductCreateSerializer(serializers.ModelSerializer):
    stock_quantity = serializers.IntegerField(min_value=0, default=0)
    low_stock_threshold = serializers.IntegerField(min_value=0, default=5)
    image_url = serializers.URLField(required=False, allow_blank=True)

    class Meta:
        model = Product
        fields = [
            "name",
            "sku",
            "description",
            "price",
            "stock_quantity",
            "low_stock_threshold",
            "is_active",
            "image_url",
        ]

    def validate_name(self, value: str) -> str:
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Enter a product name.")
        return name

    def validate_sku(self, value: str) -> str:
        sku = value.strip().upper()
        if not sku:
            raise serializers.ValidationError("Enter a SKU.")
        store = self.context["store"]
        if Product.objects.filter(store=store, sku=sku).exists():
            raise serializers.ValidationError("A product with this SKU already exists in this store.")
        return sku

    def validate_price(self, value: Decimal) -> Decimal:
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value

    def create(self, validated_data):
        store = self.context["store"]
        return create_product(store=store, **validated_data)


class ProductUpdateSerializer(serializers.ModelSerializer):
    image_url = serializers.URLField(required=False, allow_blank=True)

    class Meta:
        model = Product
        fields = [
            "name",
            "sku",
            "description",
            "price",
            "low_stock_threshold",
            "is_active",
            "image_url",
        ]

    def validate_name(self, value: str) -> str:
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Enter a product name.")
        return name

    def validate_sku(self, value: str) -> str:
        sku = value.strip().upper()
        if not sku:
            raise serializers.ValidationError("Enter a SKU.")
        store = self.instance.store
        qs = Product.objects.filter(store=store, sku=sku).exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A product with this SKU already exists in this store.")
        return sku

    def update(self, instance, validated_data):
        return update_product(product=instance, **validated_data)


class AdjustStockSerializer(serializers.Serializer):
    delta = serializers.IntegerField()
    reason = serializers.CharField(max_length=255)

    def validate_delta(self, value: int) -> int:
        if value == 0:
            raise serializers.ValidationError("Delta must be non-zero.")
        return value

    def validate_reason(self, value: str) -> str:
        reason = value.strip()
        if not reason:
            raise serializers.ValidationError("Enter a reason.")
        return reason

    def save(self, **kwargs):
        product = self.context["product"]
        user = self.context["request"].user
        try:
            return adjust_stock(
                product=product,
                delta=self.validated_data["delta"],
                reason=self.validated_data["reason"],
                user=user,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            ) from exc


class InventoryAdjustmentSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True, default=None)

    class Meta:
        model = InventoryAdjustment
        fields = [
            "id",
            "delta",
            "quantity_before",
            "quantity_after",
            "reason",
            "created_by_email",
            "created_at",
        ]
        read_only_fields = fields


class Channel3SearchSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=200)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=30, default=10)
    page_token = serializers.CharField(required=False, allow_blank=True)

    def validate_query(self, value: str) -> str:
        query = value.strip()
        if not query:
            raise serializers.ValidationError("Enter a search query.")
        return query

    def create(self, validated_data):
        try:
            return search_products(
                query=validated_data["query"],
                limit=validated_data.get("limit", 10),
                page_token=validated_data.get("page_token") or None,
            )
        except Channel3Error as exc:
            _raise_channel3(exc)


class Channel3ResultSerializer(serializers.Serializer):
    channel3_product_id = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    image_url = serializers.CharField(allow_blank=True)
    suggested_price = serializers.CharField(allow_null=True, required=False)
    currency = serializers.CharField()
    brand = serializers.CharField(allow_null=True, required=False)
    availability = serializers.CharField(allow_null=True, required=False)


class Channel3SearchResponseSerializer(serializers.Serializer):
    results = Channel3ResultSerializer(many=True)
    next_page_token = serializers.CharField(allow_null=True, required=False)


class ImportFromChannel3Serializer(serializers.Serializer):
    channel3_product_id = serializers.CharField(max_length=64)
    sku = serializers.CharField(max_length=64)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    stock_quantity = serializers.IntegerField(min_value=0, default=0)
    low_stock_threshold = serializers.IntegerField(min_value=0, default=5)

    def validate_sku(self, value: str) -> str:
        sku = value.strip().upper()
        if not sku:
            raise serializers.ValidationError("Enter a SKU.")
        return sku

    def create(self, validated_data):
        store = self.context["store"]
        channel3_id = validated_data["channel3_product_id"].strip()
        try:
            payload = retrieve_product(channel3_id)
        except Channel3Error as exc:
            if exc.status_code == 404:
                raise serializers.ValidationError({"channel3_product_id": str(exc)}) from exc
            _raise_channel3(exc)

        return import_product_from_channel3(
            store=store,
            channel3_product_id=channel3_id,
            sku=validated_data["sku"],
            price=validated_data["price"],
            stock_quantity=validated_data["stock_quantity"],
            low_stock_threshold=validated_data["low_stock_threshold"],
            channel3_payload=payload,
        )

from rest_framework import serializers


class MoneyKpiSerializer(serializers.Serializer):
    value = serializers.DecimalField(max_digits=14, decimal_places=2)
    previous = serializers.DecimalField(max_digits=14, decimal_places=2)


class CountKpiSerializer(serializers.Serializer):
    value = serializers.IntegerField()
    previous = serializers.IntegerField()


class StatusCountSerializer(serializers.Serializer):
    status = serializers.CharField()
    count = serializers.IntegerField()


# ------------------------------------------------------------------ store


class StoreKpisSerializer(serializers.Serializer):
    revenue = MoneyKpiSerializer()
    orders = CountKpiSerializer()
    average_order_value = MoneyKpiSerializer()
    new_customers = CountKpiSerializer()


class StoreSeriesPointSerializer(serializers.Serializer):
    date = serializers.DateField()
    orders = serializers.IntegerField()
    revenue = serializers.DecimalField(max_digits=14, decimal_places=2)


class TopProductSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    name = serializers.CharField()
    sku = serializers.CharField()
    quantity = serializers.IntegerField()
    revenue = serializers.DecimalField(max_digits=14, decimal_places=2)


class LowStockProductSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    sku = serializers.CharField()
    stock_quantity = serializers.IntegerField()
    low_stock_threshold = serializers.IntegerField()


class RecentOrderSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    number = serializers.CharField()
    customer_name = serializers.CharField()
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()
    fulfilment_status = serializers.CharField()
    payment_status = serializers.CharField()
    created_at = serializers.DateTimeField()


class StoreDashboardSerializer(serializers.Serializer):
    range = serializers.CharField()
    currency = serializers.CharField()
    kpis = StoreKpisSerializer()
    open_orders = serializers.IntegerField()
    orders_by_fulfilment = StatusCountSerializer(many=True)
    orders_by_payment = StatusCountSerializer(many=True)
    series = StoreSeriesPointSerializer(many=True)
    top_products = TopProductSerializer(many=True)
    low_stock = LowStockProductSerializer(many=True)
    recent_orders = RecentOrderSerializer(many=True)


# ------------------------------------------------------------------ platform


class PlatformKpisSerializer(serializers.Serializer):
    stores = CountKpiSerializer()
    subscription_revenue_cents = CountKpiSerializer()


class PlatformTotalsSerializer(serializers.Serializer):
    stores = serializers.IntegerField()
    users = serializers.IntegerField()
    active_users = serializers.IntegerField()


class PlatformSeriesPointSerializer(serializers.Serializer):
    date = serializers.DateField()
    new_stores = serializers.IntegerField()
    subscription_revenue_cents = serializers.IntegerField()


class CurrencyTotalsSerializer(serializers.Serializer):
    currency = serializers.CharField()
    orders = serializers.IntegerField()
    stores = serializers.IntegerField()
    revenue = serializers.DecimalField(max_digits=16, decimal_places=2, allow_null=True)


class TopStoreSerializer(serializers.Serializer):
    store_id = serializers.IntegerField()
    name = serializers.CharField()
    currency = serializers.CharField()
    orders = serializers.IntegerField()
    revenue = serializers.DecimalField(max_digits=16, decimal_places=2)


class PlatformDashboardSerializer(serializers.Serializer):
    range = serializers.CharField()
    kpis = PlatformKpisSerializer()
    totals = PlatformTotalsSerializer()
    stores_by_status = StatusCountSerializer(many=True)
    subscriptions_by_status = StatusCountSerializer(many=True)
    series = PlatformSeriesPointSerializer(many=True)
    orders_by_currency = CurrencyTotalsSerializer(many=True)
    top_stores = TopStoreSerializer(many=True)

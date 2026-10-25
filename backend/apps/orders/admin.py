from django.contrib import admin

from apps.orders.models import Order, OrderEvent, OrderLine


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 0
    readonly_fields = (
        "product",
        "product_name",
        "sku",
        "unit_price",
        "quantity",
        "line_total",
    )
    can_delete = False


class OrderEventInline(admin.TabularInline):
    model = OrderEvent
    extra = 0
    readonly_fields = (
        "event_type",
        "from_value",
        "to_value",
        "message",
        "actor",
        "created_at",
    )
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "store",
        "customer",
        "fulfilment_status",
        "payment_status",
        "total",
        "created_at",
    )
    list_filter = ("fulfilment_status", "payment_status", "store")
    search_fields = ("number", "customer__name")
    raw_id_fields = ("store", "customer", "created_by")
    inlines = [OrderLineInline, OrderEventInline]


@admin.register(OrderLine)
class OrderLineAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "sku", "quantity", "line_total")
    raw_id_fields = ("order", "product")


@admin.register(OrderEvent)
class OrderEventAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "event_type", "from_value", "to_value", "created_at")
    raw_id_fields = ("order", "actor")

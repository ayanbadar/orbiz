from django.contrib import admin

from apps.products.models import InventoryAdjustment, Product


class InventoryAdjustmentInline(admin.TabularInline):
    model = InventoryAdjustment
    extra = 0
    readonly_fields = ("delta", "quantity_before", "quantity_after", "reason", "created_by", "created_at")
    can_delete = False


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sku",
        "name",
        "store",
        "price",
        "stock_quantity",
        "is_active",
        "channel3_product_id",
    )
    list_filter = ("is_active", "store")
    search_fields = ("name", "sku", "channel3_product_id")
    raw_id_fields = ("store",)
    inlines = [InventoryAdjustmentInline]


@admin.register(InventoryAdjustment)
class InventoryAdjustmentAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "delta", "quantity_before", "quantity_after", "reason", "created_at")
    raw_id_fields = ("product", "created_by")

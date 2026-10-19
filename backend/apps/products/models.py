from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.stores.models import Store


class Product(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=64)
    description = models.TextField(blank=True, default="")
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    currency = models.CharField(max_length=3)
    stock_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True)
    image_url = models.URLField(max_length=2048, blank=True, default="")
    channel3_product_id = models.CharField(max_length=64, blank=True, default="")
    channel3_source = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["store", "sku"], name="uniq_store_sku"),
            models.UniqueConstraint(
                fields=["store", "channel3_product_id"],
                condition=~models.Q(channel3_product_id=""),
                name="uniq_store_channel3_product",
            ),
        ]
        indexes = [
            models.Index(fields=["store", "is_active"]),
            models.Index(fields=["store", "channel3_product_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.sku} — {self.name}"

    @property
    def is_low_stock(self) -> bool:
        return self.stock_quantity <= self.low_stock_threshold


class InventoryAdjustment(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="adjustments")
    delta = models.IntegerField()
    quantity_before = models.PositiveIntegerField()
    quantity_after = models.PositiveIntegerField()
    reason = models.CharField(max_length=255)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_adjustments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.product_id} {self.delta:+d} ({self.reason})"

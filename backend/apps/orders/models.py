from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.customers.models import Customer
from apps.products.models import Product
from apps.stores.models import Store


class Order(models.Model):
    class FulfilmentStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        UNFULFILLED = "unfulfilled", "Unfulfilled"
        PROCESSING = "processing", "Processing"
        SHIPPED = "shipped", "Shipped"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="orders")
    number = models.CharField(max_length=32)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    fulfilment_status = models.CharField(
        max_length=32,
        choices=FulfilmentStatus.choices,
        default=FulfilmentStatus.DRAFT,
    )
    payment_status = models.CharField(
        max_length=32,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
    )
    currency = models.CharField(max_length=3)
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    delivery_notes = models.TextField(blank=True, default="")
    internal_notes = models.TextField(blank=True, default="")
    source_message = models.TextField(blank=True, default="")
    stock_deducted = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["store", "number"], name="uniq_store_order_number"),
        ]
        indexes = [
            models.Index(fields=["store", "fulfilment_status"]),
            models.Index(fields=["store", "payment_status"]),
            models.Index(fields=["store", "created_at"]),
        ]

    def __str__(self) -> str:
        return self.number


class OrderLine(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_lines",
    )
    product_name = models.CharField(max_length=255)
    sku = models.CharField(max_length=64)
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["order", "product"], name="uniq_order_product_line"),
        ]

    def __str__(self) -> str:
        return f"{self.order_id}:{self.sku} x{self.quantity}"


class OrderEvent(models.Model):
    class EventType(models.TextChoices):
        CREATED = "created", "Created"
        UPDATED = "updated", "Updated"
        CONFIRMED = "confirmed", "Confirmed"
        STATUS_CHANGED = "status_changed", "Status changed"
        PAYMENT_STATUS_CHANGED = "payment_status_changed", "Payment status changed"
        CANCELLED = "cancelled", "Cancelled"
        NOTE = "note", "Note"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=32, choices=EventType.choices)
    from_value = models.CharField(max_length=64, blank=True, default="")
    to_value = models.CharField(max_length=64, blank=True, default="")
    message = models.TextField(blank=True, default="")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.order_id} {self.event_type}"

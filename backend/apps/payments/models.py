import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.orders.models import Order


class PaymentCheckout(models.Model):
    class Status(models.TextChoices):
        CREATED = "created", "Created"
        APPROVED = "approved", "Approved"
        CAPTURED = "captured", "Captured"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="paypal_checkouts",
    )
    paypal_order_id = models.CharField(max_length=64, unique=True)
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.CREATED,
    )
    approve_url = models.URLField(max_length=2048, blank=True, default="")
    capture_id = models.CharField(max_length=64, blank=True, default="")
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    currency = models.CharField(max_length=3)
    is_sandbox = models.BooleanField(default=True)
    last_error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["order", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.paypal_order_id} ({self.status})"


class PaymentRefund(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    class Source(models.TextChoices):
        ORBIZ = "orbiz", "Orbiz"
        PAYPAL = "paypal", "PayPal dashboard"

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="paypal_refunds",
    )
    capture_id = models.CharField(max_length=64)
    # Null until PayPal answers (unique + nullable: Postgres allows many NULLs).
    paypal_refund_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
    # Sent as PayPal-Request-Id so retrying a refund replays it instead of repeating it.
    request_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING,
    )
    source = models.CharField(
        max_length=16,
        choices=Source.choices,
        default=Source.ORBIZ,
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    currency = models.CharField(max_length=3)
    note_to_payer = models.CharField(max_length=255, blank=True, default="")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="paypal_refunds",
    )
    last_error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["order", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.paypal_refund_id or self.request_id} ({self.status})"


class PaymentInvoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"  # the buyer was emailed (by PayPal or by Orbiz)
        SHARED = "shared", "Shared link"  # payable by link only, nothing emailed
        PAID = "paid", "Paid"
        PARTIALLY_REFUNDED = "partially_refunded", "Partially refunded"
        REFUNDED = "refunded", "Refunded"
        CANCELLED = "cancelled", "Cancelled"
        FAILED = "failed", "Failed"

    class Delivery(models.TextChoices):
        PAYPAL = "paypal", "PayPal email"
        ORBIZ = "orbiz", "Orbiz email"
        NONE = "none", "Link only"

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="paypal_invoices",
    )
    # Null until PayPal creates the draft (unique + nullable: Postgres allows many NULLs).
    paypal_invoice_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
    invoice_number = models.CharField(max_length=25, unique=True)
    request_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    recipient_email = models.EmailField(blank=True, default="")
    delivered_via = models.CharField(
        max_length=8,
        choices=Delivery.choices,
        default=Delivery.NONE,
    )
    recipient_view_url = models.URLField(max_length=2048, blank=True, default="")
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    currency = models.CharField(max_length=3)
    # PayPal payment id of the buyer's payment — the capture an invoice refund targets.
    capture_id = models.CharField(max_length=64, blank=True, default="")
    is_sandbox = models.BooleanField(default=True)
    last_error = models.TextField(blank=True, default="")
    sent_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["order", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.invoice_number} ({self.status})"


class PayPalWebhookEvent(models.Model):
    event_id = models.CharField(max_length=64, unique=True)
    event_type = models.CharField(max_length=128)
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="paypal_webhook_events",
    )
    payload = models.JSONField(default=dict)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-received_at", "-id"]

    def __str__(self) -> str:
        return f"{self.event_type} {self.event_id}"

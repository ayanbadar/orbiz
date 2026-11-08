from django.db import models

from apps.stores.models import Store

PLAN_PRICE_CENTS = 500
PLAN_PERIOD_DAYS = 30


class Subscription(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past due"
        CANCELED = "canceled", "Canceled"

    store = models.OneToOneField(Store, on_delete=models.CASCADE, related_name="subscription")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PAST_DUE)
    amount_cents = models.PositiveIntegerField(default=PLAN_PRICE_CENTS)
    current_period_end = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.store_id}: {self.status}"


class Payment(models.Model):
    """Mock payment record. No real card data is ever stored."""

    class Status(models.TextChoices):
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="payments")
    amount_cents = models.PositiveIntegerField()
    status = models.CharField(max_length=16, choices=Status.choices)
    reference = models.CharField(max_length=40, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.reference} {self.status}"

from django.conf import settings
from django.db import models


class Store(models.Model):
    class BusinessType(models.TextChoices):
        SOCIAL = "social", "Social commerce"
        STOREFRONT = "storefront", "Online storefront"
        WHOLESALE = "wholesale", "Wholesale"
        OTHER = "other", "Other"

    name = models.CharField(max_length=120)
    currency = models.CharField(max_length=3, default="USD")
    timezone = models.CharField(max_length=64, default="UTC")
    business_type = models.CharField(
        max_length=32,
        choices=BusinessType.choices,
        default=BusinessType.SOCIAL,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class StoreMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        MEMBER = "member", "Member"

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="store_memberships",
    )
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.OWNER)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["store", "user"], name="uniq_store_user_membership"),
        ]
        ordering = ["-is_default", "created_at"]

    def __str__(self) -> str:
        return f"{self.user_id} @ {self.store_id} ({self.role})"

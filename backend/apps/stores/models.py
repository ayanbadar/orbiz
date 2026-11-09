from django.conf import settings
from django.db import models


class Store(models.Model):
    class BusinessType(models.TextChoices):
        SOCIAL = "social", "Social commerce"
        STOREFRONT = "storefront", "Online storefront"
        WHOLESALE = "wholesale", "Wholesale"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "Pending payment"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"

    name = models.CharField(max_length=120)
    currency = models.CharField(max_length=3, default="USD")
    timezone = models.CharField(max_length=64, default="UTC")
    business_type = models.CharField(
        max_length=32,
        choices=BusinessType.choices,
        default=BusinessType.SOCIAL,
    )
    # pending_payment: waiting for the subscription; suspended: blocked by the platform admin.
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_PAYMENT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Role(models.Model):
    """A store-defined bundle of permission codes (see permission_codes.py)."""

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="roles")
    name = models.CharField(max_length=60)
    description = models.CharField(max_length=200, blank=True)
    permissions = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["store", "name"], name="uniq_store_role_name"),
        ]
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} @ {self.store_id}"


class StoreMembership(models.Model):
    """Every user belongs to at most one store. Store admins have no role; staff have one."""

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="memberships")
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="membership",
    )
    is_store_admin = models.BooleanField(default=False)
    role = models.ForeignKey(Role, null=True, blank=True, on_delete=models.PROTECT, related_name="memberships")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.user_id} @ {self.store_id}"

    def has_permission(self, code: str) -> bool:
        if self.is_store_admin:
            return True
        return bool(self.role and code in self.role.permissions)

    def permission_codes(self) -> list[str]:
        from apps.stores.permission_codes import ALL_PERMISSIONS

        if self.is_store_admin:
            return list(ALL_PERMISSIONS)
        return list(self.role.permissions) if self.role else []

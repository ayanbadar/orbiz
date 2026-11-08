from django.conf import settings
from django.db import models

from apps.stores.models import Role, Store


class Invitation(models.Model):
    """Email invite. Store-admin invites create the store on accept; staff invites join a store."""

    class Kind(models.TextChoices):
        STORE_ADMIN = "store_admin", "Store admin"
        STAFF = "staff", "Staff"

    email = models.EmailField()
    token = models.CharField(max_length=64, unique=True)
    kind = models.CharField(max_length=16, choices=Kind.choices)
    store = models.ForeignKey(Store, null=True, blank=True, on_delete=models.CASCADE, related_name="invitations")
    store_name = models.CharField(max_length=120, blank=True)
    role = models.ForeignKey(Role, null=True, blank=True, on_delete=models.CASCADE, related_name="invitations")
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="sent_invitations",
    )
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.email} ({self.kind})"

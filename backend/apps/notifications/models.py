from django.db import models


class EmailStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"


class EmailLog(models.Model):
    """One row per outbound email, including messages that have not been sent yet."""

    kind = models.CharField(max_length=64, blank=True)
    # Ties a message to what caused it (e.g. "order:61:invoice:2") so callers can
    # de-duplicate sends and show the latest delivery status.
    reference = models.CharField(max_length=128, blank=True, default="", db_index=True)
    recipient = models.EmailField()
    sender = models.CharField(max_length=255)
    reply_to = models.EmailField(blank=True, default="")
    subject = models.CharField(max_length=255)
    body = models.TextField()
    html_body = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=16,
        choices=EmailStatus.choices,
        default=EmailStatus.QUEUED,
    )
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["recipient"]),
        ]

    def __str__(self) -> str:
        return f"{self.recipient}: {self.subject}"

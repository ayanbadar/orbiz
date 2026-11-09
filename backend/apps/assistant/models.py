from django.conf import settings
from django.db import models

from apps.orders.models import Order
from apps.stores.models import Store


class AssistantConversation(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="assistant_conversations")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assistant_conversations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"Conversation {self.pk} ({self.store_id})"


class AssistantMessage(models.Model):
    class ItemType(models.TextChoices):
        MESSAGE = "message", "Message"
        FUNCTION_CALL = "function_call", "Function call"
        FUNCTION_CALL_OUTPUT = "function_call_output", "Function call output"

    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    conversation = models.ForeignKey(
        AssistantConversation, on_delete=models.CASCADE, related_name="messages"
    )
    item_type = models.CharField(max_length=24, choices=ItemType.choices)
    role = models.CharField(max_length=16, choices=Role.choices, blank=True, default="")
    content = models.TextField(blank=True, default="")
    tool_name = models.CharField(max_length=64, blank=True, default="")
    # Responses API's pairing key between a function_call item and its function_call_output.
    call_id = models.CharField(max_length=64, blank=True, default="")
    tool_arguments = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return f"{self.conversation_id}:{self.item_type}"


class AssistantAction(models.Model):
    class ActionType(models.TextChoices):
        REFUND = "refund", "Refund"
        CAPTURE = "capture", "Capture"
        IMPORT_PRODUCT = "import_product", "Import product"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="assistant_actions")
    conversation = models.ForeignKey(
        AssistantConversation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="actions",
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="assistant_actions",
    )
    action_type = models.CharField(max_length=32, choices=ActionType.choices)
    payload = models.JSONField(blank=True, default=dict)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    result_message = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assistant_actions_created",
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assistant_actions_resolved",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["store", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.action_type} on order {self.order_id} ({self.status})"


class AssistantCreatedOrder(models.Model):
    """
    Anchors a Draft order to the conversation turn that created it, so its card renders back
    in its own original position in the timeline on reload — never re-triggered by some other,
    later action that merely touches the same order (checkout, invoice, cancel, ...).
    """

    conversation = models.ForeignKey(
        AssistantConversation, on_delete=models.CASCADE, related_name="created_order_links"
    )
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return f"{self.conversation_id}:order {self.order_id}"

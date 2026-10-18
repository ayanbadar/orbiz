from django.contrib import admin

from apps.notifications.models import EmailLog


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ("recipient", "subject", "kind", "status", "created_at", "sent_at")
    list_filter = ("status", "kind")
    search_fields = ("recipient", "subject", "body")
    ordering = ("-created_at",)
    readonly_fields = (
        "kind",
        "recipient",
        "sender",
        "subject",
        "body",
        "status",
        "error_message",
        "created_at",
        "updated_at",
        "sent_at",
    )

    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

from django.contrib import admin

from apps.assistant.models import AssistantAction, AssistantConversation, AssistantMessage


@admin.register(AssistantConversation)
class AssistantConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "created_by", "created_at", "updated_at")
    raw_id_fields = ("store", "created_by")


@admin.register(AssistantMessage)
class AssistantMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "item_type", "role", "tool_name", "created_at")
    list_filter = ("item_type",)
    raw_id_fields = ("conversation",)


@admin.register(AssistantAction)
class AssistantActionAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "action_type", "status", "order", "created_at", "resolved_at")
    list_filter = ("action_type", "status")
    raw_id_fields = ("store", "conversation", "order", "created_by", "resolved_by")

from django.contrib import admin

from apps.invitations.models import Invitation


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "kind", "store", "expires_at", "accepted_at")
    raw_id_fields = ("store", "role", "invited_by")

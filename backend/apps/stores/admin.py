from django.contrib import admin

from apps.stores.models import Store, StoreMembership


class StoreMembershipInline(admin.TabularInline):
    model = StoreMembership
    extra = 0
    raw_id_fields = ("user",)


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "currency", "timezone", "business_type", "created_at")
    search_fields = ("name",)
    list_filter = ("business_type", "currency")
    inlines = [StoreMembershipInline]


@admin.register(StoreMembership)
class StoreMembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "user", "role", "is_default", "created_at")
    list_filter = ("role", "is_default")
    raw_id_fields = ("store", "user")

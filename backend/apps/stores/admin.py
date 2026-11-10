from django.contrib import admin

from apps.stores.models import Role, Store, StoreMembership


class StoreMembershipInline(admin.TabularInline):
    model = StoreMembership
    extra = 0
    raw_id_fields = ("user",)


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "status", "currency", "timezone", "business_type", "created_at")
    search_fields = ("name",)
    list_filter = ("status", "business_type", "currency")
    inlines = [StoreMembershipInline]


@admin.register(StoreMembership)
class StoreMembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "user", "is_store_admin", "role", "created_at")
    list_filter = ("is_store_admin",)
    raw_id_fields = ("store", "user")


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "name")
    raw_id_fields = ("store",)

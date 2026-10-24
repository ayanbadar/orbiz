from django.contrib import admin

from apps.customers.models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "phone", "store", "updated_at")
    list_filter = ("store",)
    search_fields = ("name", "email", "phone")
    raw_id_fields = ("store",)

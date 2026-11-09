from django.contrib import admin

from apps.billing.models import Payment, Subscription

admin.site.register(Subscription)
admin.site.register(Payment)

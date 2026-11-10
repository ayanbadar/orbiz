from datetime import timedelta

from django.db import migrations
from django.utils import timezone


def grandfather_stores(apps, schema_editor):
    """Stores created before billing existed start with a paid 30-day period."""
    Store = apps.get_model("stores", "Store")
    Subscription = apps.get_model("billing", "Subscription")
    period_end = timezone.now() + timedelta(days=30)
    for store in Store.objects.filter(subscription__isnull=True):
        Subscription.objects.create(store=store, status="active", amount_cents=500, current_period_end=period_end)


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0001_initial"),
        ("stores", "0003_membership_cleanup"),
    ]

    operations = [migrations.RunPython(grandfather_stores, migrations.RunPython.noop)]

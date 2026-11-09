import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Schema cleanup after 0002's data conversion (kept separate: Postgres forbids mixing them)."""

    dependencies = [
        ("stores", "0002_tenancy_roles"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(name="storemembership", options={"ordering": ["created_at"]}),
        migrations.RemoveField(model_name="storemembership", name="legacy_role"),
        migrations.RemoveField(model_name="storemembership", name="is_default"),
        migrations.AlterField(
            model_name="storemembership",
            name="user",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="membership",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]

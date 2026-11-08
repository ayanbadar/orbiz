import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

STAFF_READ_PERMISSIONS = ["products.read", "orders.read", "customers.read"]


def convert_memberships(apps, schema_editor):
    """owner -> store admin; member -> default read-only "Staff" role; one membership per user."""
    Membership = apps.get_model("stores", "StoreMembership")
    Role = apps.get_model("stores", "Role")

    seen_users: set[int] = set()
    # Default workspace first, then oldest: keep that one, drop the rest.
    for membership in Membership.objects.order_by("-is_default", "created_at", "id"):
        if membership.user_id in seen_users:
            membership.delete()
            continue
        seen_users.add(membership.user_id)
        if membership.legacy_role == "owner":
            membership.is_store_admin = True
        else:
            role, _ = Role.objects.get_or_create(
                store_id=membership.store_id,
                name="Staff",
                defaults={"description": "Read-only access", "permissions": STAFF_READ_PERMISSIONS},
            )
            membership.role_id = role.pk
        membership.save(update_fields=["is_store_admin", "role"])


class Migration(migrations.Migration):
    dependencies = [
        ("stores", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Existing stores keep working: they start active, new ones default to pending_payment.
        migrations.AddField(
            model_name="store",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending_payment", "Pending payment"),
                    ("active", "Active"),
                    ("suspended", "Suspended"),
                ],
                default="active",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="store",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending_payment", "Pending payment"),
                    ("active", "Active"),
                    ("suspended", "Suspended"),
                ],
                default="pending_payment",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="Role",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=60)),
                ("description", models.CharField(blank=True, max_length=200)),
                ("permissions", models.JSONField(default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "store",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="roles",
                        to="stores.store",
                    ),
                ),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.AddConstraint(
            model_name="role",
            constraint=models.UniqueConstraint(fields=("store", "name"), name="uniq_store_role_name"),
        ),
        # --- StoreMembership: owner/member string -> store-admin flag + Role FK, one per user ---
        migrations.RemoveConstraint(model_name="storemembership", name="uniq_store_user_membership"),
        migrations.RenameField(model_name="storemembership", old_name="role", new_name="legacy_role"),
        migrations.AddField(
            model_name="storemembership",
            name="is_store_admin",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="storemembership",
            name="role",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="memberships",
                to="stores.role",
            ),
        ),
        migrations.RunPython(convert_memberships, migrations.RunPython.noop),
    ]

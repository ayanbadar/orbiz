from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0001_initial"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="product",
            constraint=models.UniqueConstraint(
                condition=models.Q(("channel3_product_id", ""), _negated=True),
                fields=("store", "channel3_product_id"),
                name="uniq_store_channel3_product",
            ),
        ),
    ]

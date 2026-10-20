from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0002_uniq_store_channel3_product"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="image_url",
            field=models.URLField(blank=True, default="", max_length=2048),
        ),
    ]

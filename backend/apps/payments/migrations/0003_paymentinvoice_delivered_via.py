from django.db import migrations, models


def tag_existing_sent_invoices(apps, schema_editor):
    # Before this field existed, any invoice sent to a recipient was emailed by PayPal
    # (whatever its status is now: sent, paid, cancelled, refunded).
    PaymentInvoice = apps.get_model("payments", "PaymentInvoice")
    PaymentInvoice.objects.filter(sent_at__isnull=False).exclude(recipient_email="").update(
        delivered_via="paypal"
    )


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0002_paymentinvoice_paymentrefund'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentinvoice',
            name='delivered_via',
            field=models.CharField(choices=[('paypal', 'PayPal email'), ('orbiz', 'Orbiz email'), ('none', 'Link only')], default='none', max_length=8),
        ),
        migrations.RunPython(tag_existing_sent_invoices, migrations.RunPython.noop),
    ]

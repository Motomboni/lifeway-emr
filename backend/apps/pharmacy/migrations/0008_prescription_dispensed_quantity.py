from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0007_eprescription_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='prescription',
            name='dispensed_quantity',
            field=models.CharField(
                blank=True,
                help_text="Exact quantity dispensed by pharmacist (e.g., '24 tablets', '1 bottle')",
                max_length=100,
            ),
        ),
    ]


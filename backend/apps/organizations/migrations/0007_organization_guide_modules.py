# Generated migration for guide_modules on Organization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0006_paystack_recurring_subscription"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="guide_modules",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Enabled Guide modules (laboratory, pharmacy, radiology, nhia, anc, telemedicine)",
            ),
        ),
    ]

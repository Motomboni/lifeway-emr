# Generated for SaaS multi-tenancy

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0001_initial"),
        ("visits", "0006_timelineevent"),
    ]

    operations = [
        migrations.AddField(
            model_name="visit",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                help_text="Organization (tenant) - set from patient.organization",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="visits",
                to="organizations.organization",
            ),
        ),
        migrations.AddIndex(
            model_name="visit",
            index=models.Index(fields=["organization"], name="visits_organiz_idx"),
        ),
    ]

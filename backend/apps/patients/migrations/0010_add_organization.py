# Generated for SaaS multi-tenancy

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0001_initial"),
        ("patients", "0009_national_health_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="patient",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                help_text="Organization (tenant) this patient belongs to",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="patients",
                to="organizations.organization",
            ),
        ),
        migrations.AddIndex(
            model_name="patient",
            index=models.Index(fields=["organization"], name="patients_organiz_idx"),
        ),
    ]

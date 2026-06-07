from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0001_initial"),
        ("pharmacy", "0007_eprescription_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="drug",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                help_text="Organization (tenant). Null = legacy/global template.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="drugs",
                to="organizations.organization",
            ),
        ),
        migrations.AddIndex(
            model_name="drug",
            index=models.Index(fields=["organization"], name="drugs_organiz_idx"),
        ),
    ]

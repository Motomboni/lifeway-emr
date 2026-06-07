# Generated for SaaS multi-tenancy

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0001_initial"),
        ("billing", "0020_claimpolicy_claim"),
    ]

    operations = [
        migrations.AddField(
            model_name="servicecatalog",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                help_text="Organization (tenant). Null = legacy/global template.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="service_catalog",
                to="organizations.organization",
            ),
        ),
        migrations.AddIndex(
            model_name="servicecatalog",
            index=models.Index(fields=["organization"], name="service_cat_organiz_idx"),
        ),
    ]

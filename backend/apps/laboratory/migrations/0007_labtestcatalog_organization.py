from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0001_initial"),
        ("laboratory", "0006_alter_labresult_lab_order"),
    ]

    operations = [
        migrations.AddField(
            model_name="labtestcatalog",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                help_text="Organization (tenant). Null = legacy/global template.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="lab_test_catalog",
                to="organizations.organization",
            ),
        ),
        migrations.AddIndex(
            model_name="labtestcatalog",
            index=models.Index(fields=["organization"], name="lab_test_cat_organiz_idx"),
        ),
    ]

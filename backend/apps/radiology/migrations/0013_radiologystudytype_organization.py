from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0001_initial"),
        ("radiology", "0012_radiologyrequest_finding_flag"),
    ]

    operations = [
        migrations.AddField(
            model_name="radiologystudytype",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                help_text="Organization (tenant). Null = legacy/global template.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="radiology_study_types",
                to="organizations.organization",
            ),
        ),
        migrations.AddIndex(
            model_name="radiologystudytype",
            index=models.Index(fields=["organization"], name="rad_study_type_org_idx"),
        ),
    ]

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("radiology", "0014_rename_rad_study_type_org_idx_radiology_s_organiz_9a708b_idx"),
    ]

    operations = [
        migrations.AlterField(
            model_name="radiologystudy",
            name="radiology_order",
            field=models.OneToOneField(
                blank=True,
                help_text="Legacy radiology order (optional)",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="study",
                to="radiology.radiologyorder",
            ),
        ),
        migrations.AddField(
            model_name="radiologystudy",
            name="radiology_request",
            field=models.OneToOneField(
                blank=True,
                help_text="Service Catalog radiology request this study belongs to",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="pacs_study",
                to="radiology.radiologyrequest",
            ),
        ),
        migrations.AddIndex(
            model_name="radiologystudy",
            index=models.Index(
                fields=["radiology_request"], name="radiology_s_radiolo_idx"
            ),
        ),
    ]

# Generated manually for SaaS multi-tenancy

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("patients", "0010_add_organization"),
    ]

    operations = [
        migrations.AlterField(
            model_name="patient",
            name="patient_id",
            field=models.CharField(
                help_text="Internal patient ID (unique per organization, auto-generated)",
                max_length=50,
            ),
        ),
        migrations.AddConstraint(
            model_name="patient",
            constraint=models.UniqueConstraint(
                fields=("organization", "patient_id"),
                name="patients_unique_patient_id_per_org",
            ),
        ),
    ]

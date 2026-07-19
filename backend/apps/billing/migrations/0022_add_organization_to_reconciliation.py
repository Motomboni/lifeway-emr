# Generated for SaaS multi-tenancy - scope EndOfDayReconciliation by organization

from django.db import migrations, models
import django.db.models.deletion


def assign_default_org(apps, schema_editor):
    """Assign existing reconciliations to default organization."""
    EndOfDayReconciliation = apps.get_model("billing", "EndOfDayReconciliation")
    Organization = apps.get_model("organizations", "Organization")
    default_org = (
        Organization.objects.filter(slug="default-clinic").first()
        or Organization.objects.first()
    )
    if (
        not default_org
        and EndOfDayReconciliation.objects.filter(organization__isnull=True).exists()
    ):
        default_org, _ = Organization.objects.get_or_create(
            slug="default-clinic",
            defaults={
                "name": "Default Clinic",
                "patient_id_prefix": "LMC",
                "is_active": True,
            },
        )
    if default_org:
        EndOfDayReconciliation.objects.filter(organization__isnull=True).update(
            organization=default_org
        )


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0001_initial"),
        ("billing", "0021_add_servicecatalog_organization"),
    ]

    operations = [
        migrations.AddField(
            model_name="endofdayreconciliation",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="reconciliations",
                to="organizations.organization",
                help_text="Organization (tenant) for this reconciliation",
            ),
        ),
        migrations.AlterField(
            model_name="endofdayreconciliation",
            name="reconciliation_date",
            field=models.DateField(
                db_index=True, help_text="Date of reconciliation (one per org per day)"
            ),
        ),
        migrations.RunPython(assign_default_org, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="endofdayreconciliation",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="reconciliations",
                to="organizations.organization",
                help_text="Organization (tenant) for this reconciliation",
            ),
        ),
        migrations.AddIndex(
            model_name="endofdayreconciliation",
            index=models.Index(
                fields=["organization", "reconciliation_date"],
                name="end_of_day_org_date_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="endofdayreconciliation",
            constraint=models.UniqueConstraint(
                fields=("organization", "reconciliation_date"),
                name="end_of_day_org_date_unique",
            ),
        ),
    ]

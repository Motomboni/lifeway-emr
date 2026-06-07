# Set default limits on Starter plan for SaaS enforcement

from django.db import migrations


def set_starter_limits(apps, schema_editor):
    Plan = apps.get_model("organizations", "Plan")
    Plan.objects.filter(slug="starter").update(
        max_users=10,
        max_patients=500,
    )


def reverse_migration(apps, schema_editor):
    Plan = apps.get_model("organizations", "Plan")
    Plan.objects.filter(slug="starter").update(
        max_users=None,
        max_patients=None,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0002_create_default_org_and_assign"),
    ]

    operations = [
        migrations.RunPython(set_starter_limits, reverse_migration),
    ]

# Data migration: create default organization and assign existing data

from django.db import migrations


def create_default_org_and_assign(apps, schema_editor):
    """Create default organization and assign all existing data to it."""
    Organization = apps.get_model("organizations", "Organization")
    Plan = apps.get_model("organizations", "Plan")
    Subscription = apps.get_model("organizations", "Subscription")
    Patient = apps.get_model("patients", "Patient")
    Visit = apps.get_model("visits", "Visit")
    ServiceCatalog = apps.get_model("billing", "ServiceCatalog")
    User = apps.get_model("users", "User")
    OrganizationUser = apps.get_model("organizations", "OrganizationUser")

    # Create default organization if we have any data to migrate
    has_patients = Patient.objects.exists()
    has_services = ServiceCatalog.objects.exists()

    if has_patients or has_services:
        org, _ = Organization.objects.get_or_create(
            slug="default-clinic",
            defaults={
                "name": "Default Clinic",
                "patient_id_prefix": "LMC",
                "is_active": True,
            },
        )

        # Create free plan and subscription
        plan, _ = Plan.objects.get_or_create(
            slug="starter",
            defaults={
                "name": "Starter",
                "price_monthly": 0,
                "currency": "NGN",
                "is_active": True,
                "sort_order": 0,
            },
        )
        Subscription.objects.get_or_create(
            organization=org, defaults={"plan": plan, "status": "ACTIVE"}
        )

        # Assign patients
        Patient.objects.filter(organization__isnull=True).update(organization=org)

        # Assign visits (via patient.organization)
        Visit.objects.filter(organization__isnull=True).update(organization=org)

        # Assign service catalog
        ServiceCatalog.objects.filter(organization__isnull=True).update(
            organization=org
        )

        # Add all staff users (non-PATIENT) to the default org
        for user in User.objects.filter(
            role__in=[
                "ADMIN",
                "DOCTOR",
                "NURSE",
                "LAB_TECH",
                "RADIOLOGY_TECH",
                "PHARMACIST",
                "RECEPTIONIST",
                "IVF_SPECIALIST",
                "EMBRYOLOGIST",
            ]
        ):
            OrganizationUser.objects.get_or_create(
                organization=org,
                user=user,
                defaults={
                    "role": "ADMIN" if user.role == "ADMIN" else "MEMBER",
                    "is_default": True,
                },
            )


def reverse_migration(apps, schema_editor):
    """Reverse: set organization to null (data will remain)."""
    Patient = apps.get_model("patients", "Patient")
    Visit = apps.get_model("visits", "Visit")
    ServiceCatalog = apps.get_model("billing", "ServiceCatalog")
    Patient.objects.update(organization=None)
    Visit.objects.update(organization=None)
    ServiceCatalog.objects.update(organization=None)


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0001_initial"),
        ("patients", "0010_add_organization"),
        ("visits", "0007_add_organization"),
        ("billing", "0021_add_servicecatalog_organization"),
    ]

    operations = [
        migrations.RunPython(create_default_org_and_assign, reverse_migration),
    ]

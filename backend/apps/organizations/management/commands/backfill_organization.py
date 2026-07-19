"""Assign NULL organization rows and staff memberships to the default Lifeway clinic."""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.organizations.models import Organization, OrganizationUser, Plan
from apps.patients.models import Patient
from apps.users.models import User
from apps.visits.models import Visit

STAFF_ROLES = [
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


class Command(BaseCommand):
    help = (
        "Backfill organization on patients/visits and ensure staff belong to the "
        "default clinic (slug default-clinic)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--slug",
            default="default-clinic",
            help="Organization slug (default: default-clinic)",
        )
        parser.add_argument(
            "--name",
            default="Lifeway Medical Center",
            help="Organization display name when creating the org",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        slug = options["slug"]
        name = options["name"]

        org, created = Organization.objects.get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "patient_id_prefix": "LMC",
                "is_active": True,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created organization: {org.name}"))
        else:
            self.stdout.write(f"Using organization: {org.name} ({org.slug})")

        patients_updated = Patient.objects.filter(organization__isnull=True).update(
            organization=org
        )
        visits_updated = Visit.objects.filter(organization__isnull=True).update(
            organization=org
        )

        memberships_created = 0
        for user in User.objects.filter(role__in=STAFF_ROLES):
            _, was_created = OrganizationUser.objects.get_or_create(
                organization=org,
                user=user,
                defaults={
                    "role": "ADMIN" if user.role == "ADMIN" else "MEMBER",
                    "is_default": True,
                },
            )
            if was_created:
                memberships_created += 1

        # Lifeway single-clinic: no caps on the default starter plan
        plans_updated = Plan.objects.filter(slug="starter").update(
            max_patients=None,
            max_users=None,
        )

        self.stdout.write(
            f"Patients updated: {patients_updated}, "
            f"visits updated: {visits_updated}, "
            f"new memberships: {memberships_created}, "
            f"starter plan limits cleared: {plans_updated}"
        )

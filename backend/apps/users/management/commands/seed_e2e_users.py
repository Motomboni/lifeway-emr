"""
Seed Playwright E2E test users with organization membership.

Usage:
    python manage.py seed_e2e_users

Idempotent — safe to run before every E2E suite (also invoked from Playwright global-setup).
"""

from django.core.management.base import BaseCommand
from django.db import transaction

E2E_USERS = [
    {
        "username": "doctor@clinic.com",
        "email": "doctor@clinic.com",
        "password": "Doctor123!",
        "first_name": "Test",
        "last_name": "Doctor",
        "role": "DOCTOR",
    },
    {
        "username": "receptionist@clinic.com",
        "email": "receptionist@clinic.com",
        "password": "Receptionist123!",
        "first_name": "Test",
        "last_name": "Receptionist",
        "role": "RECEPTIONIST",
    },
    {
        "username": "labtech@clinic.com",
        "email": "labtech@clinic.com",
        "password": "LabTech123!",
        "first_name": "Test",
        "last_name": "Lab Tech",
        "role": "LAB_TECH",
    },
]


class Command(BaseCommand):
    help = "Create or update E2E test users and attach them to the default clinic org"

    @transaction.atomic
    def handle(self, *args, **options):
        from apps.organizations.models import Organization, OrganizationUser, Plan, Subscription
        from apps.users.models import User

        org = Organization.objects.filter(slug="default-clinic", is_active=True).first()
        if not org:
            org = Organization.objects.filter(is_active=True).order_by("id").first()
        if not org:
            org = Organization.objects.create(
                name="E2E Test Clinic",
                slug="e2e-clinic",
                patient_id_prefix="LMC",
                is_active=True,
            )
            self.stdout.write(self.style.SUCCESS(f"Created organization: {org.slug}"))

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
            organization=org,
            defaults={"plan": plan, "status": "ACTIVE"},
        )

        for spec in E2E_USERS:
            user = User.objects.filter(username=spec["username"]).first()
            if user:
                user.email = spec["email"]
                user.first_name = spec["first_name"]
                user.last_name = spec["last_name"]
                user.role = spec["role"]
                user.is_active = True
                user.set_password(spec["password"])
                user.save()
                created = False
            else:
                user = User.objects.create_user(
                    username=spec["username"],
                    email=spec["email"],
                    password=spec["password"],
                    first_name=spec["first_name"],
                    last_name=spec["last_name"],
                    role=spec["role"],
                    is_active=True,
                )
                created = True

            OrganizationUser.objects.update_or_create(
                organization=org,
                user=user,
                defaults={"role": "MEMBER", "is_default": True},
            )

            verb = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"  {verb} {spec['role']}: {spec['email']}"))

        self._seed_service_catalog(org)
        self._seed_hmo_provider(org)

        self.stdout.write(
            self.style.SUCCESS(
                f"\nE2E users ready on org “{org.name}” (id={org.id}, slug={org.slug})"
            )
        )

    def _seed_service_catalog(self, org):
        from decimal import Decimal

        from apps.billing.service_catalog_models import ServiceCatalog

        fixtures = [
            {
                "service_code": "REG-001",
                "name": "Patient Intake",
                "amount": Decimal("2000.00"),
                "department": "CONSULTATION",
                "category": "CONSULTATION",
                "workflow_type": "OTHER",
                "auto_bill": True,
                "bill_timing": "BEFORE",
                "restricted_service_flag": True,
                "allowed_roles": ["RECEPTIONIST", "ADMIN"],
            },
            {
                "service_code": "CONS-001",
                "name": "General Consultation",
                "amount": Decimal("5000.00"),
                "department": "CONSULTATION",
                "category": "CONSULTATION",
                "workflow_type": "GOPD_CONSULT",
                "auto_bill": True,
                "bill_timing": "AFTER",
                "restricted_service_flag": True,
                "allowed_roles": ["DOCTOR", "RECEPTIONIST", "ADMIN"],
            },
            {
                "service_code": "CBC-001",
                "name": "Complete Blood Count",
                "amount": Decimal("5000.00"),
                "department": "LAB",
                "category": "LAB",
                "workflow_type": "LAB_ORDER",
                "auto_bill": True,
                "bill_timing": "AFTER",
                "restricted_service_flag": False,
                "allowed_roles": ["DOCTOR", "NURSE", "ADMIN"],
            },
        ]

        for spec in fixtures:
            ServiceCatalog.objects.update_or_create(
                service_code=spec["service_code"],
                defaults={**spec, "organization": org, "is_active": True},
            )
            self.stdout.write(
                self.style.SUCCESS(f"  Service catalog: {spec['service_code']}")
            )

    def _seed_hmo_provider(self, _org):
        from apps.billing.insurance_models import HMOProvider
        from apps.users.models import User

        receptionist = User.objects.filter(username="receptionist@clinic.com").first()
        if not receptionist:
            return

        provider, created = HMOProvider.objects.update_or_create(
            code="E2E-HMO",
            defaults={
                "name": "E2E Test HMO",
                "is_active": True,
                "created_by": receptionist,
            },
        )
        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"  {verb} HMO provider: {provider.code}"))

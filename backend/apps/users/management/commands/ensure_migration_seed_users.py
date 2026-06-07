"""
Create minimal users required for legacy data import (migrate_lmc load.py).

Idempotent: creates migration_doctor, migration_pharmacist, and migration_receptionist if missing.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.users.models import User


class Command(BaseCommand):
    help = "Ensure DOCTOR, PHARMACIST, and RECEPTIONIST users exist for LIFEWAY/LMC migration loaders."

    @transaction.atomic
    def handle(self, *args, **options):
        if not User.objects.filter(username="migration_doctor").exists():
            doctor = User(
                username="migration_doctor",
                email="migration-doctor@example.invalid",
                first_name="Migration",
                last_name="Doctor",
                role="DOCTOR",
                is_staff=False,
                is_active=True,
            )
            doctor.set_unusable_password()
            doctor.save()
            self.stdout.write(self.style.SUCCESS("Created migration_doctor"))
        else:
            self.stdout.write("migration_doctor already exists")

        if not User.objects.filter(username="migration_pharmacist").exists():
            pharm = User(
                username="migration_pharmacist",
                email="migration-pharmacist@example.invalid",
                first_name="Migration",
                last_name="Pharmacist",
                role="PHARMACIST",
                is_staff=False,
                is_active=True,
            )
            pharm.set_unusable_password()
            pharm.save()
            self.stdout.write(self.style.SUCCESS("Created migration_pharmacist"))
        else:
            self.stdout.write("migration_pharmacist already exists")

        if not User.objects.filter(username="migration_receptionist").exists():
            receptionist = User(
                username="migration_receptionist",
                email="migration-receptionist@example.invalid",
                first_name="Migration",
                last_name="Receptionist",
                role="RECEPTIONIST",
                is_staff=False,
                is_active=True,
            )
            receptionist.set_unusable_password()
            receptionist.save()
            self.stdout.write(self.style.SUCCESS("Created migration_receptionist"))
        else:
            self.stdout.write("migration_receptionist already exists")

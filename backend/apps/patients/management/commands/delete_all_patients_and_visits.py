"""
Django management command to delete all Patient and Visit records.

Uses superuser purge context to bypass compliance delete guards.

Usage:
    python manage.py delete_all_patients_and_visits
    python manage.py delete_all_patients_and_visits --confirm
"""

from django.core.management.base import BaseCommand

from apps.patients.models import Patient
from apps.visits.models import Visit
from core.purge_service import purge_all_patients_and_visits


class Command(BaseCommand):
    help = (
        "Delete all Patient and Visit records from the database "
        "(cascade deletes all related records)"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Skip confirmation prompt and delete immediately",
        )

    def handle(self, *args, **options):
        patient_count = Patient.objects.count()
        visit_count = Visit.objects.count()

        if patient_count == 0 and visit_count == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    "No patients or visits found in the database. Nothing to delete."
                )
            )
            return

        self.stdout.write(
            self.style.WARNING(
                f"\nWARNING: This will delete {patient_count} patient(s), "
                f"{visit_count} visit(s), and ALL related records.\n"
                "This action CANNOT be undone!\n"
            )
        )

        if not options["confirm"]:
            confirm = input('\nType "DELETE ALL PATIENTS AND VISITS" to confirm: ')
            if confirm != "DELETE ALL PATIENTS AND VISITS":
                self.stdout.write(
                    self.style.ERROR(
                        "Deletion cancelled. Confirmation text did not match."
                    )
                )
                return

        try:
            stats = purge_all_patients_and_visits()
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSuccessfully deleted {stats.get('patients_deleted', 0)} patient(s), "
                    f"{stats.get('visits_deleted', 0)} visit(s), and related records."
                )
            )
            for key, value in sorted(stats.items()):
                if key not in ("patients_deleted", "visits_deleted") and value:
                    self.stdout.write(f"  - {key}: {value}")
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"\nError deleting patients and visits: {str(e)}")
            )
            raise

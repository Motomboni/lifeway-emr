"""Backfill PatientAllergy rows from legacy Patient.allergies free text."""

from django.core.management.base import BaseCommand

from apps.clinical.alert_service import parse_allergy_tokens
from apps.patients.allergy_models import PatientAllergy
from apps.patients.models import Patient


class Command(BaseCommand):
    help = "Import legacy free-text allergies into structured PatientAllergy records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report counts without writing to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        created = 0
        skipped = 0
        patients_touched = 0

        qs = Patient.objects.filter(is_active=True).exclude(allergies__isnull=True).exclude(
            allergies=""
        )

        for patient in qs.iterator():
            tokens = parse_allergy_tokens(patient.allergies)
            if not tokens:
                continue
            patients_touched += 1
            for token in tokens:
                label = token.strip().title()
                if not label:
                    continue
                exists = PatientAllergy.objects.filter(
                    patient=patient,
                    allergen__iexact=label,
                    is_active=True,
                ).exists()
                if exists:
                    skipped += 1
                    continue
                if dry_run:
                    created += 1
                    continue
                PatientAllergy.objects.create(
                    patient=patient,
                    allergen=label,
                    allergen_type="UNKNOWN",
                    severity="UNKNOWN",
                    source="LEGACY_TEXT",
                    verified=False,
                    is_active=True,
                )
                created += 1

        mode = " (dry run)" if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"Patients scanned: {patients_touched}; "
                f"allergies created{mode}: {created}; skipped (duplicate): {skipped}"
            )
        )

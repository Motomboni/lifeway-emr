"""
Mark migrated legacy Payment rows with positive amounts as CLEARED.

LIFEWAY tblPatientPayment exports often have empty/non-standard Status while
PayAmount is set — those rows are historical receipts, not open pending payments.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.billing.models import Payment

LEGACY_PAYMENT_PREFIX = "[Legacy PatientPayID:"


class Command(BaseCommand):
    help = "Set CLEARED on legacy payments that have a positive migrated amount but PENDING status."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report how many rows would change without updating the database.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        queryset = Payment.objects.filter(
            notes__startswith=LEGACY_PAYMENT_PREFIX,
            status="PENDING",
            amount__gt=Decimal("0"),
        ).exclude(
            Q(notes__icontains="REFUND")
            | Q(notes__icontains="VOID")
            | Q(notes__icontains="REVERSE")
        )
        total = queryset.count()
        if dry_run:
            self.stdout.write(self.style.WARNING(f"Dry run: would update {total} legacy payment(s) to CLEARED."))
            return

        updated = queryset.update(status="CLEARED")
        self.stdout.write(self.style.SUCCESS(f"Updated {updated} legacy payment(s) to CLEARED."))

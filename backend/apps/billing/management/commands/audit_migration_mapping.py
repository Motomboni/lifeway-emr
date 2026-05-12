"""
Audit and safely repair post-migration workflow mapping.

This command does not create BillingLineItems from legacy VisitCharges because
BillingService already includes both sources in totals. Creating duplicate
line items from charges would inflate patient balances.
"""
import os
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum

from apps.billing.billing_line_item_models import BillingLineItem
from apps.billing.billing_line_item_service import allocate_payment_to_line_items
from apps.billing.billing_service import BillingService
from apps.billing.models import Payment, VisitCharge
from apps.laboratory.models import LabOrder
from apps.patients.models import Patient
from apps.pharmacy.models import Prescription
from apps.radiology.models import RadiologyRequest
from apps.visits.models import Visit


class Command(BaseCommand):
    help = "Audit migrated records and apply safe workflow-mapping repairs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--legacy-prefix",
            default=(os.environ.get("LEGACY_PATIENT_ID_PREFIX") or "LIFEWAYLEG"),
            help="Migrated patient_id prefix. Defaults to LEGACY_PATIENT_ID_PREFIX or LIFEWAYLEG.",
        )
        parser.add_argument(
            "--activate-patients",
            action="store_true",
            help="Set is_active=True for migrated patients that have visits.",
        )
        parser.add_argument(
            "--sync-visit-payment-status",
            action="store_true",
            help="Recompute and persist migrated visit payment_status where safe.",
        )
        parser.add_argument(
            "--allocate-payments",
            action="store_true",
            help="Allocate existing cleared payments to existing BillingLineItems.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report intended write changes without saving.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Optional visit processing limit for sync/allocation actions.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Print every per-visit repair candidate.",
        )
        parser.add_argument(
            "--sample-size",
            type=int,
            default=20,
            help="Number of per-visit repair candidates to print when not verbose.",
        )

    def handle(self, *args, **options):
        prefix = (options["legacy_prefix"] or "").strip()
        if not prefix:
            self.stdout.write(self.style.ERROR("legacy-prefix cannot be empty."))
            return

        dry_run = options["dry_run"]
        verbose = options["verbose"]
        sample_size = max(options["sample_size"], 0)
        migrated_patients = Patient.objects.filter(patient_id__startswith=prefix)
        migrated_visits = Visit.objects.filter(
            patient__patient_id__startswith=prefix
        ).distinct().order_by("id")
        if options["limit"]:
            visit_ids = list(migrated_visits.values_list("id", flat=True)[: options["limit"]])
            migrated_visits = Visit.objects.filter(id__in=visit_ids).order_by("id")

        inactive_with_visits = migrated_patients.filter(
            is_active=False,
            visits__isnull=False,
        ).distinct()
        visits_with_charges_and_no_line_items = migrated_visits.filter(
            charges__isnull=False,
            billing_line_items__isnull=True,
        ).distinct()
        visits_with_both_charge_sources = migrated_visits.filter(
            charges__isnull=False,
            billing_line_items__isnull=False,
        ).distinct()

        self.stdout.write(self.style.SUCCESS("Migration workflow mapping audit"))
        self.stdout.write(f"Legacy patient prefix: {prefix}")
        self.stdout.write(f"Dry run: {dry_run}")
        self.stdout.write("")
        self.stdout.write(f"Patients: {migrated_patients.count()}")
        self.stdout.write(f"Patients inactive but attached to visits: {inactive_with_visits.count()}")
        self.stdout.write(f"Visits: {migrated_visits.count()}")
        self.stdout.write(f"Payments: {Payment.objects.filter(visit__in=migrated_visits).count()}")
        self.stdout.write(f"VisitCharges: {VisitCharge.objects.filter(visit__in=migrated_visits).count()}")
        self.stdout.write(f"BillingLineItems: {BillingLineItem.objects.filter(visit__in=migrated_visits).count()}")
        self.stdout.write(f"LabOrders: {LabOrder.objects.filter(visit__in=migrated_visits).count()}")
        self.stdout.write(f"RadiologyRequests: {RadiologyRequest.objects.filter(visit__in=migrated_visits).count()}")
        self.stdout.write(f"Prescriptions: {Prescription.objects.filter(visit__in=migrated_visits).count()}")
        self.stdout.write(
            "Visits with legacy charges but no BillingLineItems: "
            f"{visits_with_charges_and_no_line_items.count()}"
        )
        self.stdout.write(
            "Visits with both VisitCharges and BillingLineItems (double-count risk): "
            f"{visits_with_both_charge_sources.count()}"
        )

        if options["activate_patients"]:
            self._activate_patients(inactive_with_visits, dry_run)

        if options["sync_visit_payment_status"]:
            self._sync_visit_payment_status(migrated_visits, dry_run, verbose, sample_size)

        if options["allocate_payments"]:
            self._allocate_payments(migrated_visits, dry_run, verbose, sample_size)

    def _activate_patients(self, queryset, dry_run):
        count = queryset.count()
        self.stdout.write("")
        self.stdout.write(f"Activating migrated patients with visits: {count}")
        if dry_run:
            return
        updated = queryset.update(is_active=True)
        self.stdout.write(self.style.SUCCESS(f"Activated patients: {updated}"))

    def _sync_visit_payment_status(self, visits, dry_run, verbose, sample_size):
        changed = 0
        skipped_double_count_risk = 0
        samples = []

        self.stdout.write("")
        self.stdout.write("Syncing visit payment statuses from BillingService...")
        for visit in visits:
            has_charges = VisitCharge.objects.filter(visit=visit).exists()
            has_line_items = BillingLineItem.objects.filter(visit=visit).exists()
            if has_charges and has_line_items:
                skipped_double_count_risk += 1
                continue

            summary = BillingService.compute_billing_summary(visit)
            if summary.payment_status == visit.payment_status:
                continue

            changed += 1
            message = f"Visit {visit.id}: {visit.payment_status} -> {summary.payment_status}"
            if verbose:
                self.stdout.write(message)
            elif len(samples) < sample_size:
                samples.append(message)
            if not dry_run:
                Visit.objects.filter(pk=visit.pk).update(payment_status=summary.payment_status)

        self.stdout.write(f"Visits needing status update: {changed}")
        self.stdout.write(f"Skipped double-count-risk visits: {skipped_double_count_risk}")
        if samples:
            self.stdout.write("Sample status updates:")
            for message in samples:
                self.stdout.write(f"  {message}")
            if changed > len(samples):
                self.stdout.write(f"  ... {changed - len(samples)} more")
        if changed and not dry_run:
            self.stdout.write(self.style.SUCCESS("Payment statuses synced."))

    def _allocate_payments(self, visits, dry_run, verbose, sample_size):
        updated_visits = 0
        total_allocated = Decimal("0.00")
        samples = []

        self.stdout.write("")
        self.stdout.write("Allocating existing payments to existing BillingLineItems...")
        for visit in visits:
            line_items = BillingLineItem.objects.filter(visit=visit)
            if not line_items.exists():
                continue

            total_paid = (
                Payment.objects.filter(visit=visit, status="CLEARED").aggregate(total=Sum("amount"))["total"]
                or Decimal("0.00")
            )
            already_allocated = line_items.aggregate(total=Sum("amount_paid"))["total"] or Decimal("0.00")
            unallocated = total_paid - already_allocated
            if unallocated <= 0:
                continue

            updated_visits += 1
            total_allocated += unallocated
            message = f"Visit {visit.id}: allocate {unallocated}"
            if verbose:
                self.stdout.write(message)
            elif len(samples) < sample_size:
                samples.append(message)
            if not dry_run:
                with transaction.atomic():
                    allocate_payment_to_line_items(visit, unallocated, "CASH")

        self.stdout.write(f"Visits with allocatable payment: {updated_visits}")
        self.stdout.write(f"Total allocatable amount: {total_allocated}")
        if samples:
            self.stdout.write("Sample allocations:")
            for message in samples:
                self.stdout.write(f"  {message}")
            if updated_visits > len(samples):
                self.stdout.write(f"  ... {updated_visits - len(samples)} more")
        if updated_visits and not dry_run:
            self.stdout.write(self.style.SUCCESS("Payment allocation complete."))

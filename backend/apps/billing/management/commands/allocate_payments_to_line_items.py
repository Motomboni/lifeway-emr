"""
One-time backfill: allocate existing Payments to BillingLineItems so payment_gates work.

Before this change, creating a Payment did not update BillingLineItem.bill_status,
so registration_paid and consultation_paid stayed false even after payment.
This command allocates already-recorded payments to line items (Registration first,
then Consultation, then others) so payment gates reflect reality.

Usage:
    python manage.py allocate_payments_to_line_items
    python manage.py allocate_payments_to_line_items --visit 244
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Sum

from apps.visits.models import Visit
from apps.billing.billing_line_item_models import BillingLineItem
from apps.billing.billing_service import BillingService
from apps.billing.billing_line_item_service import allocate_payment_to_line_items


class Command(BaseCommand):
    help = (
        "Allocate existing CLEARED payments to BillingLineItems (Registration first, "
        "then Consultation, then others) so payment_gates.registration_paid and "
        "consultation_paid become true where payment was already collected."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--visit",
            type=int,
            default=None,
            help="Run only for this visit ID (default: all visits with BillingLineItems)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only report what would be allocated, do not update.",
        )

    def handle(self, *args, **options):
        visit_id = options["visit"]
        dry_run = options["dry_run"]

        if visit_id:
            visits = Visit.objects.filter(pk=visit_id)
            if not visits.exists():
                self.stdout.write(self.style.ERROR(f"Visit {visit_id} not found."))
                return
        else:
            # Visits that have at least one BillingLineItem
            visits = Visit.objects.filter(
                billing_line_items__isnull=False
            ).distinct().order_by("id")

        total_visits = 0
        updated_visits = 0

        for visit in visits:
            total_visits += 1
            total_cleared = (
                BillingService._compute_total_payments(visit)
                + BillingService._compute_total_wallet_debits(visit)
            )
            total_allocated = (
                BillingLineItem.objects.filter(visit=visit).aggregate(
                    s=Sum("amount_paid")
                )["s"]
                or Decimal("0.00")
            )
            unallocated = total_cleared - total_allocated
            if unallocated <= 0:
                continue
            updated_visits += 1
            self.stdout.write(
                f"Visit {visit.id}: total_cleared={total_cleared} "
                f"allocated={total_allocated} -> allocate {unallocated}"
            )
            if not dry_run:
                try:
                    allocate_payment_to_line_items(visit, unallocated, "CASH")
                    self.stdout.write(self.style.SUCCESS(f"  Allocated for visit {visit.id}"))
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"  Failed visit {visit.id}: {e}")
                    )

        self.stdout.write("")
        self.stdout.write(
            f"Visits with BillingLineItems: {total_visits}, "
            f"visits with unallocated payment: {updated_visits}"
        )
        if dry_run and updated_visits:
            self.stdout.write(
                self.style.WARNING("Run without --dry-run to apply allocation.")
            )

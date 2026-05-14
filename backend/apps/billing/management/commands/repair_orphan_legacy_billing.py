"""
Re-attribute LIFEWAY orphan billing rows (PatientID=0) off LIFEWAYLEG0000000.

Rows were incorrectly dumped onto Legacy Patient 0 / visit 12411. Payments are
reattributed by payer name; receipt lines by receipt number.
"""
from __future__ import annotations

import os
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.billing.legacy_orphan_attribution import (
    dump_patient_external_id,
    ensure_backfill_visit,
    ensure_payer_stub_patient,
    ensure_receipt_stub_patient,
    extract_legacy_pay_id,
    extract_legacy_receipt_id,
    load_payment_csv_index,
    load_receipt_csv_index,
    parse_legacy_datetime,
)
from apps.billing.models import Payment, VisitCharge
from apps.patients.models import Patient


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _default_csv_dir() -> Path:
    return _repo_root() / "tmp" / "lifeway_csv"


class Command(BaseCommand):
    help = "Move orphan legacy billing rows off LIFEWAYLEG0000000 onto payer/receipt stub patients."

    def add_arguments(self, parser):
        parser.add_argument("--csv-dir", default="", help="LIFEWAY CSV directory (default: tmp/lifeway_csv).")
        parser.add_argument("--dry-run", action="store_true", help="Report counts only.")
        parser.add_argument(
            "--legacy-prefix",
            default=(os.environ.get("LEGACY_PATIENT_ID_PREFIX") or "LIFEWAYLEG"),
        )

    def handle(self, *args, **options):
        prefix = (options["legacy_prefix"] or "LIFEWAYLEG").strip()
        csv_dir = Path(options["csv_dir"]) if options["csv_dir"] else _default_csv_dir()
        dry_run = bool(options["dry_run"])

        dump_patient = Patient.objects.filter(patient_id=dump_patient_external_id(prefix)).only("id").first()
        if not dump_patient:
            self.stdout.write(self.style.WARNING("Dump patient LIFEWAYLEG0000000 not found; nothing to repair."))
            return

        payment_rows = load_payment_csv_index(csv_dir)
        receipt_rows = load_receipt_csv_index(csv_dir)
        if not payment_rows and not receipt_rows:
            self.stdout.write(self.style.ERROR(f"No LIFEWAY CSV indexes found in {csv_dir}"))
            return

        payments = list(
            Payment.objects.filter(visit__patient_id=dump_patient.id).only("id", "visit_id", "notes", "created_at")
        )
        charges = list(
            VisitCharge.objects.filter(visit__patient_id=dump_patient.id).only(
                "id", "visit_id", "description", "created_at"
            )
        )
        self.stdout.write(
            f"Found {len(payments)} payment(s) and {len(charges)} charge(s) on dump patient {dump_patient_external_id(prefix)}."
        )

        if dry_run:
            pay_moves = sum(
                1
                for payment in payments
                if (pay_id := extract_legacy_pay_id(payment.notes))
                and payment_rows.get(pay_id, {}).get("payer")
            )
            charge_moves = sum(
                1
                for charge in charges
                if (line_id := extract_legacy_receipt_id(charge.description))
                and line_id in receipt_rows
            )
            self.stdout.write(self.style.WARNING(f"Dry run: would move {pay_moves} payment(s) and {charge_moves} charge(s)."))
            return

        patient_cache: dict[str, int] = {}
        visit_cache: dict[tuple[int, str], int] = {}
        moved_payments = 0
        moved_charges = 0
        skipped_payments = 0
        skipped_charges = 0

        with transaction.atomic():
            for payment in payments:
                pay_id = extract_legacy_pay_id(payment.notes)
                row = payment_rows.get(pay_id or -1)
                payer = (row or {}).get("payer", "").strip()
                if not payer:
                    skipped_payments += 1
                    continue
                event_dt = parse_legacy_datetime((row or {}).get("payment_date") or payment.created_at)
                patient_pk = ensure_payer_stub_patient(prefix, payer, patient_cache)
                visit_pk = ensure_backfill_visit(patient_pk, event_dt, visit_cache)
                if payment.visit_id != visit_pk:
                    Payment.objects.filter(pk=payment.pk).update(visit_id=visit_pk)
                    moved_payments += 1

            for charge in charges:
                line_id = extract_legacy_receipt_id(charge.description)
                row = receipt_rows.get(line_id or -1)
                if not row:
                    skipped_charges += 1
                    continue
                event_dt = parse_legacy_datetime(row.get("line_date") or charge.created_at)
                patient_pk = ensure_receipt_stub_patient(prefix, row.get("receipt_no"), patient_cache)
                visit_pk = ensure_backfill_visit(patient_pk, event_dt, visit_cache)
                if charge.visit_id != visit_pk:
                    VisitCharge.objects.filter(pk=charge.pk).update(visit_id=visit_pk)
                    moved_charges += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Moved {moved_payments} payment(s) and {moved_charges} charge(s). "
                f"Skipped {skipped_payments} payment(s), {skipped_charges} charge(s)."
            )
        )

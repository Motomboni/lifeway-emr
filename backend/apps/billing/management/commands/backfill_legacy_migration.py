"""
Backfill legacy LIFEWAY/LMC migration gaps:

- Creates stub patients for billing-only legacy PatientIDs (not in outpatient master).
- Auto-creates backfill visits when a migrated patient has billing/clinical rows but no visit.
- Re-imports payments, visit charges, lab orders/results, and vitals from LIFEWAY CSV export.
- Zero-amount legacy payments are imported as deferred VisitCharges (flexible payment / pay later).

Requires tmp/lifeway_csv (or --csv-dir) from migrate_lifeway/restore_export.py.
"""
from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.billing.models import Payment, VisitCharge
from apps.clinical.models import VitalSigns
from apps.laboratory.models import LabOrder, LabResult
from apps.patients.models import Patient
from apps.visits.models import Visit

BACKFILL_TABLES = (
    "tblPatientVisits",
    "tblPatientPayment",
    "tblTempReceipt",
    "tblLabRequest",
    "tblLabResult",
    "tblVitalSign",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _default_csv_dir() -> Path:
    return _repo_root() / "tmp" / "lifeway_csv"


def _read_csv_table(csv_dir: Path, table_name: str) -> list[dict]:
    path = csv_dir / f"{table_name}.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class Command(BaseCommand):
    help = "Backfill skipped legacy migration rows (stub patients, visits, billing, labs, vitals)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-dir",
            type=str,
            default="",
            help="Directory with LIFEWAY per-table CSV files (default: tmp/lifeway_csv).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report only; do not write patients, visits, or re-import rows.",
        )
        parser.add_argument(
            "--legacy-prefix",
            default=(os.environ.get("LEGACY_PATIENT_ID_PREFIX") or "LIFEWAYLEG"),
            help="Migrated patient_id prefix.",
        )

    def handle(self, *args, **options):
        csv_dir = Path(options["csv_dir"]) if options["csv_dir"] else _default_csv_dir()
        dry_run = options["dry_run"]
        prefix = (options["legacy_prefix"] or "").strip()

        if not csv_dir.is_dir():
            self.stdout.write(self.style.ERROR(f"CSV directory not found: {csv_dir}"))
            self.stdout.write("Export LIFEWAY data first: python backend/scripts/migrate_lifeway/restore_export.py")
            return

        before = self._legacy_counts(prefix)
        self.stdout.write(self.style.SUCCESS("Legacy migration backfill"))
        self.stdout.write(f"CSV dir: {csv_dir}")
        self.stdout.write(f"Dry run: {dry_run}")
        self.stdout.write(f"Legacy prefix: {prefix}")
        self._print_counts("Before", before)

        orphan_ids = self._orphan_patient_ids(csv_dir, prefix)
        self.stdout.write(f"Billing-only legacy PatientIDs (not in EMR): {len(orphan_ids)}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — no database changes."))
            return

        scripts_dir = _repo_root() / "backend" / "scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))

        from migrate_lmc.mapping import load_mapping_rows
        from migrate_lmc.transform import transform_source_data
        from migrate_lmc.load import load_transformed_data

        mapping_file = _repo_root() / "docs" / "migration" / "lmc-column-mapping-status.csv"
        mapping_rows = load_mapping_rows(mapping_file)

        extracted: dict[str, list[dict]] = {}
        for table in BACKFILL_TABLES:
            rows = _read_csv_table(csv_dir, table)
            if rows:
                extracted[table] = rows
                self.stdout.write(f"  Loaded {len(rows)} rows from {table}.csv")

        payloads = transform_source_data(extracted, mapping_rows)
        loaded = load_transformed_data(payloads, dry_run=False, backfill_mode=True)

        after = self._legacy_counts(prefix)
        self.stdout.write("")
        self._print_counts("After", after)
        self.stdout.write("")
        self.stdout.write("Loader counts this run:")
        for model, count in sorted(loaded.items()):
            self.stdout.write(f"  {model}: {count}")

        self.stdout.write(self.style.SUCCESS("Backfill complete."))

    def _legacy_counts(self, prefix: str) -> dict[str, int]:
        lp = Q(patient__patient_id__startswith=prefix)
        lv = Q(visit__patient__patient_id__startswith=prefix)
        return {
            "patients": Patient.objects.filter(patient_id__startswith=prefix).count(),
            "visits": Visit.objects.filter(lp).count(),
            "payments": Payment.objects.filter(lv).count(),
            "visit_charges": VisitCharge.objects.filter(lv).count(),
            "lab_orders": LabOrder.objects.filter(lv).count(),
            "lab_results": LabResult.objects.filter(lab_order__visit__patient__patient_id__startswith=prefix).count(),
            "vitals": VitalSigns.objects.filter(lv).count(),
        }

    def _print_counts(self, label: str, counts: dict[str, int]) -> None:
        self.stdout.write(f"\n{label}:")
        for key, value in counts.items():
            self.stdout.write(f"  {key}: {value}")

    def _orphan_patient_ids(self, csv_dir: Path, prefix: str) -> set[int]:
        existing_suffixes = set()
        for pid in Patient.objects.filter(patient_id__startswith=prefix).values_list("patient_id", flat=True):
            suffix = pid[len(prefix) :]
            if suffix.isdigit():
                existing_suffixes.add(int(suffix))

        orphan: set[int] = set()
        for table in ("tblPatientPayment", "tblTempReceipt", "tblLabRequest"):
            for row in _read_csv_table(csv_dir, table):
                raw = row.get("PatientID")
                if raw is None or str(raw).strip() == "":
                    continue
                try:
                    legacy_id = int(str(raw).strip())
                except ValueError:
                    continue
                if legacy_id not in existing_suffixes:
                    orphan.add(legacy_id)
        return orphan

"""Import deferred (zero-amount) LIFEWAY payments as VisitCharges — fast path for production."""
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.billing.deferred_legacy_import import import_deferred_charges_from_payment_csv
from apps.billing.models import VisitCharge


def _default_csv_dir() -> Path:
    return Path(__file__).resolve().parents[5] / "tmp" / "lifeway_csv"


class Command(BaseCommand):
    help = "Import zero-amount LIFEWAY tblPatientPayment rows as deferred VisitCharges (fast)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-dir",
            type=str,
            default="",
            help="Directory with tblPatientPayment.csv (default: tmp/lifeway_csv).",
        )
        parser.add_argument("--dry-run", action="store_true", help="Count rows only; no DB writes.")

    def handle(self, *args, **options):
        csv_dir = Path(options["csv_dir"]) if options["csv_dir"] else _default_csv_dir()
        dry_run = bool(options["dry_run"])

        if not csv_dir.is_dir():
            self.stdout.write(self.style.ERROR(f"CSV directory not found: {csv_dir}"))
            return

        before = VisitCharge.objects.filter(description__startswith="[Legacy Deferred PatientPayID:").count()
        self.stdout.write(f"Deferred charges before: {before}")
        self.stdout.write(f"CSV dir: {csv_dir}")
        self.stdout.write(f"Dry run: {dry_run}")

        def progress(index: int, stats: dict) -> None:
            self.stdout.write(
                f"  … scanned {index} payment rows; "
                f"deferred={stats['deferred_rows']} created={stats['created']} updated={stats['updated']}"
            )

        stats = import_deferred_charges_from_payment_csv(
            csv_dir,
            dry_run=dry_run,
            progress_callback=progress,
            progress_every=200,
        )

        after = (
            before
            if dry_run
            else VisitCharge.objects.filter(description__startswith="[Legacy Deferred PatientPayID:").count()
        )

        self.stdout.write("")
        self.stdout.write(f"Payment rows scanned: {stats['scanned']}")
        self.stdout.write(f"Zero-amount (deferred) rows: {stats['deferred_rows']}")
        if not dry_run:
            self.stdout.write(f"Created: {stats['created']}")
            self.stdout.write(f"Updated: {stats['updated']}")
            self.stdout.write(f"Skipped: {stats['skipped']}")
            self.stdout.write(f"Errors: {stats['errors']}")
            self.stdout.write(f"Deferred charges after: {after}")
            self.stdout.write(self.style.SUCCESS("Deferred import complete."))
        else:
            self.stdout.write(self.style.WARNING("Dry run only — no changes written."))

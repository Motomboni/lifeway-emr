"""Reassign migrated appointments from migration_doctor to LIFEWAY doctors."""
from __future__ import annotations

import csv
import os
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.appointments.legacy_appointment_attribution import (
    ensure_doctor_from_display_name,
    extract_legacy_app_id,
    format_legacy_doctor_tag,
    load_appointment_csv_index,
    promote_legacy_doctor_user,
    resolve_legacy_doctor_user,
)
from apps.appointments.models import Appointment
from apps.users.models import User


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _default_csv_dir() -> Path:
    return _repo_root() / "tmp" / "lifeway_csv"


def _load_user_name_index(csv_dir: Path) -> dict[int, str]:
    path = csv_dir / "tblUsers.csv"
    if not path.exists():
        return {}
    index: dict[int, str] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                uid = int(row["UserID"])
            except (TypeError, ValueError, KeyError):
                continue
            index[uid] = (row.get("FullName") or "").strip()
    return index


class Command(BaseCommand):
    help = "Repair migrated appointments assigned to migration_doctor."

    def add_arguments(self, parser):
        parser.add_argument("--csv-dir", default="", help="LIFEWAY CSV directory.")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--legacy-prefix",
            default=(os.environ.get("LEGACY_PATIENT_ID_PREFIX") or "LIFEWAYLEG"),
        )

    def handle(self, *args, **options):
        csv_dir = Path(options["csv_dir"]) if options["csv_dir"] else _default_csv_dir()
        dry_run = bool(options["dry_run"])
        appointment_rows = load_appointment_csv_index(csv_dir)
        user_names = _load_user_name_index(csv_dir)
        if not appointment_rows:
            self.stdout.write(self.style.ERROR(f"No appointment CSV index found in {csv_dir}"))
            return

        migration_doctor = User.objects.filter(username="migration_doctor").only("id").first()
        if not migration_doctor:
            self.stdout.write(self.style.WARNING("migration_doctor user not found."))
            return

        doctor_cache: dict[int, User] = {}
        name_cache: dict[str, User] = {}
        updated = 0
        tagged = 0
        skipped = 0

        appointments = Appointment.objects.select_related("doctor").all()
        with transaction.atomic():
            for designation_user_id, full_name in user_names.items():
                user = resolve_legacy_doctor_user(designation_user_id, cache=doctor_cache)
                if not user or not full_name:
                    continue
                parts = full_name.split()
                if len(parts) == 1:
                    first = parts[0]
                    last = ""
                else:
                    first = parts[0]
                    last = " ".join(parts[1:])
                if user.first_name != first or user.last_name != last:
                    if not dry_run:
                        User.objects.filter(pk=user.pk).update(first_name=first[:255], last_name=last[:255])
                    user.first_name = first
                    user.last_name = last
                promote_legacy_doctor_user(user)

            for appointment in appointments.iterator():
                app_id = extract_legacy_app_id(appointment.notes)
                row = appointment_rows.get(app_id or -1, {})
                doctor = resolve_legacy_doctor_user(row.get("doctor_id"), cache=doctor_cache)
                doctor_name = (row.get("doctor_name") or "").strip()

                if not doctor and doctor_name:
                    doctor = ensure_doctor_from_display_name(doctor_name, cache=name_cache)

                new_notes = appointment.notes or ""
                if doctor_name and format_legacy_doctor_tag(doctor_name) not in new_notes:
                    new_notes = f"{format_legacy_doctor_tag(doctor_name)} {new_notes}".strip()
                    tagged += 1

                if not doctor:
                    skipped += 1
                    continue

                changed = False
                if appointment.doctor_id != doctor.id:
                    changed = True
                    if not dry_run:
                        appointment.doctor_id = doctor.id
                if new_notes != (appointment.notes or ""):
                    changed = True
                    if not dry_run:
                        appointment.notes = new_notes

                if changed and not dry_run:
                    appointment.save(update_fields=["doctor_id", "notes"])
                    updated += 1
                elif changed:
                    updated += 1

        remaining = Appointment.objects.filter(doctor_id=migration_doctor.id).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Updated {updated} appointment(s); tagged {tagged} with legacy doctor name; skipped {skipped}. "
                f"Remaining on migration_doctor: {remaining}."
            )
        )

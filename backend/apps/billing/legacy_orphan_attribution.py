"""
Attribution helpers for LIFEWAY rows with PatientID=0 (orphan billing records).

These rows have payer/receipt metadata but no outpatient id. They must not be
attached to the shared stub patient LIFEWAYLEG0000000.
"""
from __future__ import annotations

import csv
import hashlib
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from django.utils import timezone

LEGACY_PAY_ID_RE = re.compile(r"\[Legacy PatientPayID:(\d+)\]")
LEGACY_RECEIPT_ID_RE = re.compile(r"\[Legacy TempReceipt:(\d+)\]")
LEGACY_BACKFILL_VISIT_TAG = "[Legacy migration backfill visit]"


def parse_payer_name(payer: str) -> tuple[str, str]:
    text = (payer or "").strip()
    if not text:
        return "Unknown", "Payer"
    if ";" in text:
        parts = [part.strip() for part in text.split(";") if part.strip()]
        if len(parts) >= 2:
            return parts[0], parts[1]
    tokens = text.split()
    if len(tokens) >= 2:
        return tokens[0], " ".join(tokens[1:])
    return text, "Payer"


def orphan_external_id(prefix: str, key: str) -> str:
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10].upper()
    return f"{prefix}O{digest}"


def payer_external_id(prefix: str, payer: str) -> str:
    norm = re.sub(r"\s+", " ", (payer or "").strip().upper())
    return orphan_external_id(prefix, f"PAYER:{norm}")


def receipt_external_id(prefix: str, receipt_no: str | int | None) -> str:
    token = str(receipt_no or "unknown").strip()
    return orphan_external_id(prefix, f"RECEIPT:{token}")


def load_payment_csv_index(csv_dir: Path) -> dict[int, dict]:
    path = csv_dir / "tblPatientPayment.csv"
    if not path.exists():
        return {}
    index: dict[int, dict] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                pay_id = int(row["PatientPayID"])
                patient_id = int(row.get("PatientID") or 0)
            except (TypeError, ValueError, KeyError):
                continue
            index[pay_id] = {
                "patient_id": patient_id,
                "payer": (row.get("PayerName") or "").strip(),
                "payment_date": row.get("PaymentDate"),
                "amount": row.get("PayAmount"),
            }
    return index


def load_receipt_csv_index(csv_dir: Path) -> dict[int, dict]:
    path = csv_dir / "tblTempReceipt.csv"
    if not path.exists():
        return {}
    index: dict[int, dict] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                line_id = int(row["TempReceiptID"])
                patient_id = int(row.get("PatientID") or 0)
            except (TypeError, ValueError, KeyError):
                continue
            index[line_id] = {
                "patient_id": patient_id,
                "receipt_no": (row.get("ReceiptNo") or "").strip(),
                "line_date": row.get("LineDate"),
                "service_line": (row.get("ServiceLine") or "").strip(),
            }
    return index


def extract_legacy_pay_id(notes: str | None) -> int | None:
    if not notes:
        return None
    match = LEGACY_PAY_ID_RE.search(notes)
    if not match:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


def extract_legacy_receipt_id(description: str | None) -> int | None:
    if not description:
        return None
    match = LEGACY_RECEIPT_ID_RE.search(description)
    if not match:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


def parse_legacy_datetime(value) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value or "").strip()
        if not text:
            return timezone.now()
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            dt = timezone.now()
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def ensure_named_stub_patient(
    *,
    prefix: str,
    external_id: str,
    first_name: str,
    last_name: str,
    cache: dict[str, int],
) -> int:
    from apps.patients.models import Patient  # pylint: disable=import-outside-toplevel

    if external_id in cache:
        return cache[external_id]
    patient, _ = Patient.objects.update_or_create(
        patient_id=external_id,
        defaults={
            "first_name": first_name[:120],
            "last_name": last_name[:120],
            "is_active": True,
        },
    )
    cache[external_id] = patient.id
    return patient.id


def ensure_payer_stub_patient(prefix: str, payer: str, cache: dict[str, int]) -> int:
    first_name, last_name = parse_payer_name(payer)
    external_id = payer_external_id(prefix, payer)
    return ensure_named_stub_patient(
        prefix=prefix,
        external_id=external_id,
        first_name=first_name,
        last_name=last_name,
        cache=cache,
    )


def ensure_receipt_stub_patient(prefix: str, receipt_no: str | int | None, cache: dict[str, int]) -> int:
    token = str(receipt_no or "unknown").strip()
    external_id = receipt_external_id(prefix, token)
    return ensure_named_stub_patient(
        prefix=prefix,
        external_id=external_id,
        first_name="Legacy",
        last_name=f"Receipt {token}"[:120],
        cache=cache,
    )


def ensure_backfill_visit(patient_pk: int, event_dt: datetime, cache: dict[tuple[int, str], int]) -> int:
    from apps.visits.models import Visit  # pylint: disable=import-outside-toplevel

    day_key = event_dt.date().isoformat()
    cache_key = (patient_pk, day_key)
    if cache_key in cache:
        return cache[cache_key]

    same_day = list(
        Visit.objects.filter(patient_id=patient_pk, created_at__date=event_dt.date()).only("id", "created_at")
    )
    if same_day:
        visit_pk = min(
            same_day,
            key=lambda visit: abs((visit.created_at - event_dt).total_seconds()) if visit.created_at else float("inf"),
        ).id
        cache[cache_key] = visit_pk
        return visit_pk

    backfill = (
        Visit.objects.filter(patient_id=patient_pk, chief_complaint__startswith=LEGACY_BACKFILL_VISIT_TAG)
        .only("id")
        .first()
    )
    if backfill:
        cache[cache_key] = backfill.id
        return backfill.id

    visit = Visit.objects.create(
        patient_id=patient_pk,
        created_at=event_dt,
        visit_type="ROUTINE",
        status="CLOSED",
        payment_status="UNPAID",
        chief_complaint=f"{LEGACY_BACKFILL_VISIT_TAG} Auto-created for orphan legacy billing row.",
        service_area="Legacy migration",
    )
    Visit.objects.filter(pk=visit.pk).update(created_at=event_dt)
    cache[cache_key] = visit.pk
    return visit.pk


def dump_patient_external_id(prefix: str) -> str:
    return f"{prefix}0000000"

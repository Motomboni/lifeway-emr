"""
Import zero-amount LIFEWAY tblPatientPayment rows as deferred VisitCharges only.

Skips positive-amount payments so production backfill completes in minutes, not hours.
"""
from __future__ import annotations

import csv
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.billing.legacy_orphan_attribution import ensure_payer_stub_patient
from apps.billing.models import VisitCharge
from apps.patients.models import Patient
from apps.visits.models import Visit

LEGACY_BACKFILL_VISIT_TAG = "[Legacy backfill visit]"
DEFERRED_TAG_PREFIX = "[Legacy Deferred PatientPayID:"


def _charge_category_from_receipt_line(field_name: Any, service_line: Any) -> str:
    blob = f"{field_name or ''} {service_line or ''}".upper()
    if any(x in blob for x in ("LAB", "PATH", "URINE", "BLOOD", "MICRO", "HISTOL")):
        return "LAB"
    if any(x in blob for x in ("XRAY", "X-RAY", "RADIO", "SCAN", "SONO", "ULTRA", " CT", "MRI", "ECHO")):
        return "RADIOLOGY"
    if any(x in blob for x in ("PHARM", "DRUG", "TAB ", " TAB", "CAP ", "SYRUP", "SUSP", "INJ ", "INSULIN", "IVFL")):
        return "DRUG"
    if any(x in blob for x in ("CONSULT", "OPD", "CLINIC", "REVIEW")):
        return "CONSULTATION"
    if any(x in blob for x in ("INJECT", "DRESS", "SUTURE", "PROC", "IUCD", "IUD ", "DRESSING")):
        return "PROCEDURE"
    return "MISC"


def _resolve_legacy_service_line_amount(service_line: str) -> Decimal | None:
    from apps.billing.legacy_deferred_service import resolve_deferred_price

    amount, _, _ = resolve_deferred_price(service_line)
    return amount if amount > 0 else None


def _to_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value).strip().replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _to_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    text = str(value).strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _ensure_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def import_deferred_charges_from_payment_csv(
    csv_dir: Path,
    *,
    dry_run: bool = False,
    progress_callback: Any | None = None,
    progress_every: int = 100,
) -> dict[str, int]:
    """
    Create/update deferred VisitCharge rows from tblPatientPayment.csv (PayAmount <= 0).
    Returns stats: scanned, deferred_rows, created, updated, skipped, errors.
    """
    payment_csv = csv_dir / "tblPatientPayment.csv"
    if not payment_csv.is_file():
        raise FileNotFoundError(f"Missing {payment_csv}")

    prefix = (os.environ.get("LEGACY_PATIENT_ID_PREFIX") or "LIFEWAYLEG").strip() or "LIFEWAYLEG"
    patient_key_prefix = prefix

    patient_id_map: dict[int, int] = {}
    for pid in Patient.objects.filter(patient_id__startswith=prefix).values_list("patient_id", "id"):
        external_id, pk = pid
        suffix = external_id[len(prefix) :]
        if suffix.isdigit():
            patient_id_map[int(suffix)] = pk

    payer_patient_map: dict[str, int] = {}
    backfill_visit_by_patient: dict[int, int] = {}
    visits_by_patient: dict[int, list[tuple[int, datetime | None]]] = {}
    for row in Visit.objects.filter(patient__patient_id__startswith=prefix).values_list(
        "patient_id", "id", "created_at"
    ):
        patient_pk, visit_pk, created_at = row
        visits_by_patient.setdefault(patient_pk, []).append((visit_pk, created_at))

    stats = {
        "scanned": 0,
        "deferred_rows": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0,
    }

    def _patient_external_id(legacy_patient_id: int) -> str:
        return f"{patient_key_prefix}{legacy_patient_id:07d}"

    def _lookup_patient_pk(legacy_patient_id: int) -> int | None:
        cached = patient_id_map.get(legacy_patient_id)
        if cached:
            return cached
        patient = Patient.objects.filter(patient_id=_patient_external_id(legacy_patient_id)).only("id").first()
        if patient:
            patient_id_map[legacy_patient_id] = patient.id
            return patient.id
        return None

    def _ensure_stub_patient(legacy_patient_id: int) -> int | None:
        external_id = _patient_external_id(legacy_patient_id)
        patient, _ = Patient.objects.update_or_create(
            patient_id=external_id,
            defaults={
                "first_name": "Legacy",
                "last_name": f"Patient {legacy_patient_id}",
                "is_active": True,
            },
        )
        patient_id_map[legacy_patient_id] = patient.id
        return patient.id

    def _ensure_backfill_visit(patient_pk: int, event_dt: datetime) -> int:
        cached = backfill_visit_by_patient.get(patient_pk)
        if cached:
            return cached
        existing = (
            Visit.objects.filter(patient_id=patient_pk, chief_complaint__startswith=LEGACY_BACKFILL_VISIT_TAG)
            .only("id")
            .first()
        )
        if existing:
            backfill_visit_by_patient[patient_pk] = existing.id
            return existing.id
        visit = Visit.objects.create(
            patient_id=patient_pk,
            created_at=event_dt,
            visit_type="ROUTINE",
            status="CLOSED",
            payment_status="UNPAID",
            chief_complaint=f"{LEGACY_BACKFILL_VISIT_TAG} Auto-created to attach migrated billing/clinical records.",
            service_area="Legacy migration",
        )
        Visit.objects.filter(pk=visit.pk).update(created_at=event_dt)
        backfill_visit_by_patient[patient_pk] = visit.id
        visits_by_patient.setdefault(patient_pk, []).append((visit.id, event_dt))
        return visit.id

    def _resolve_visit_pk(patient_pk: int, event_dt: datetime) -> int | None:
        cands = visits_by_patient.get(patient_pk, [])
        same_day = [(vid, dt) for vid, dt in cands if dt and dt.date() == event_dt.date()]
        pool = same_day or cands
        if pool:
            return min(
                pool,
                key=lambda item: abs((item[1] - event_dt).total_seconds()) if item[1] else float("inf"),
            )[0]
        if dry_run:
            return None
        return _ensure_backfill_visit(patient_pk, event_dt)

    with payment_csv.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    stats["scanned"] = len(rows)

    for index, source_row in enumerate(rows, start=1):
        legacy_pay_id = _to_int(source_row.get("PatientPayID"))
        if legacy_pay_id is None:
            stats["skipped"] += 1
            continue

        amt = _to_decimal(source_row.get("PayAmount")) or Decimal("0")
        if amt > 0:
            continue

        stats["deferred_rows"] += 1
        legacy_patient_id = _to_int(source_row.get("PatientID"))
        payer_name = (str(source_row.get("PayerName") or "")).strip()
        pay_dt = _ensure_aware(_to_datetime(source_row.get("PaymentDate"))) or timezone.now()

        if legacy_patient_id is None or legacy_patient_id <= 0:
            if dry_run:
                stats["skipped"] += 1
                continue
            patient_pk = ensure_payer_stub_patient(patient_key_prefix, payer_name, payer_patient_map)
        else:
            patient_pk = _lookup_patient_pk(legacy_patient_id)
            if not patient_pk and not dry_run:
                patient_pk = _ensure_stub_patient(legacy_patient_id)

        if not patient_pk:
            stats["skipped"] += 1
            continue

        visit_pk = _resolve_visit_pk(patient_pk, pay_dt)
        if not visit_pk:
            stats["skipped"] += 1
            continue

        svc = (str(source_row.get("ServiceLine") or "")).strip()
        dx = (str(source_row.get("DiagnosisLine") or "")).strip()
        charge_amount = _resolve_legacy_service_line_amount(svc) or Decimal("0")
        deferred_tag = f"{DEFERRED_TAG_PREFIX}{legacy_pay_id}]"
        desc_parts = [deferred_tag, (svc or "Legacy service (flexible payment)")]
        if dx:
            desc_parts.append(f"Diagnosis (legacy): {dx[:200]}")
        if charge_amount <= 0:
            desc_parts.append("Flexible payment — amount pending (not recorded in LIFEWAY export).")
        description = " — ".join(desc_parts).strip()[:255]
        category = _charge_category_from_receipt_line("", svc)

        if dry_run:
            if progress_callback and index % progress_every == 0:
                progress_callback(index, stats)
            continue

        try:
            with transaction.atomic():
                existing = VisitCharge.objects.filter(
                    visit_id=visit_pk,
                    description__startswith=deferred_tag,
                ).first()
                if existing:
                    VisitCharge.objects.filter(pk=existing.pk).update(
                        category=category,
                        description=description,
                        amount=charge_amount,
                        created_by_system=True,
                        created_at=pay_dt,
                    )
                    stats["updated"] += 1
                else:
                    charge = VisitCharge.objects.create(
                        visit_id=visit_pk,
                        category=category,
                        description=description,
                        amount=charge_amount,
                        created_by_system=True,
                    )
                    VisitCharge.objects.filter(pk=charge.pk).update(created_at=pay_dt)
                    stats["created"] += 1
                Visit.objects.filter(pk=visit_pk, payment_status="PAID").update(payment_status="UNPAID")
        except Exception:
            stats["errors"] += 1

        if progress_callback and index % progress_every == 0:
            progress_callback(index, stats)

    return stats

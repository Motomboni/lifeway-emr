"""
NHIA/HMO claim pack builder — one visit or batch export for portal upload.
"""

from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal
from typing import Any

from django.db.models import Q

from apps.ai_integration.nhia_validation import extract_codes_from_note, validate_scribe_codes
from apps.billing.models import VisitCharge
from apps.billing.nhia_charge_service import NHIA_CHARGE_PREFIX
from apps.consultations.models import Consultation
from apps.visits.models import Visit


def _patient_claim_fields(patient) -> dict[str, str]:
    return {
        "patient_id": str(patient.id),
        "patient_mrn": getattr(patient, "mrn", None) or getattr(patient, "patient_id", "") or "",
        "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
        "national_health_id": getattr(patient, "national_health_id", "") or "",
        "id_verified": str(getattr(patient, "id_verified", False)),
        "date_of_birth": str(patient.date_of_birth) if patient.date_of_birth else "",
        "phone": patient.phone or "",
    }


def _lines_from_nhia_charges(visit: Visit) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for charge in VisitCharge.objects.filter(visit=visit).order_by("created_at"):
        desc = charge.description or ""
        if NHIA_CHARGE_PREFIX not in desc:
            continue
        start = desc.index(NHIA_CHARGE_PREFIX) + len(NHIA_CHARGE_PREFIX)
        nhia = desc[start:].split("|", 1)[0].strip()
        icd11 = ""
        if "[ICD-11:" in desc:
            icd11 = desc.split("[ICD-11:", 1)[1].split("]", 1)[0].strip()
        lines.append(
            {
                "source": "nhia_charge",
                "nhia_code": nhia,
                "icd11": icd11,
                "description": desc,
                "amount_ngn": str(charge.amount),
            }
        )
    return lines


def _lines_from_consultation(visit: Visit) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    consultation = (
        Consultation.objects.filter(visit=visit).order_by("-updated_at").first()
    )
    if not consultation:
        return lines

    note_text = "\n".join(
        filter(
            None,
            [
                consultation.diagnosis,
                consultation.clinical_notes,
                consultation.history,
                consultation.examination,
            ],
        )
    )
    if not note_text.strip():
        return lines

    validation = validate_scribe_codes(note_text)
    for code in validation.get("validated_codes", []):
        if code.get("match_status") != "matched":
            continue
        lines.append(
            {
                "source": "consultation_note",
                "nhia_code": code.get("nhia", ""),
                "icd11": code.get("icd11", ""),
                "description": code.get("diagnosis") or code.get("tariff_name") or "",
                "amount_ngn": code.get("amount_ngn") or "0.00",
            }
        )

    if lines:
        return lines

    for code in extract_codes_from_note(note_text):
        lines.append(
            {
                "source": "consultation_note",
                "nhia_code": code.get("nhia", ""),
                "icd11": code.get("icd11", ""),
                "description": code.get("diagnosis") or "",
                "amount_ngn": "0.00",
            }
        )
    return lines


def build_visit_claim_pack(visit: Visit) -> dict[str, Any]:
    """Build claim pack payload for a single visit."""
    patient = visit.patient
    nhia_lines = _lines_from_nhia_charges(visit)
    note_lines = _lines_from_consultation(visit) if not nhia_lines else []

    # Prefer billed NHIA charges; supplement with note codes not yet billed
    billed_nhia = {l["nhia_code"] for l in nhia_lines}
    for line in note_lines:
        if line["nhia_code"] and line["nhia_code"] not in billed_nhia:
            nhia_lines.append(line)

    total = sum(Decimal(l["amount_ngn"] or "0") for l in nhia_lines)
    return {
        "visit_id": visit.id,
        "visit_date": str(visit.created_at.date()) if visit.created_at else "",
        "visit_status": visit.status,
        "payment_status": visit.payment_status,
        **(_patient_claim_fields(patient)),
        "line_items": nhia_lines,
        "line_count": len(nhia_lines),
        "total_amount_ngn": str(total),
        "claim_ready": len(nhia_lines) > 0
        and bool(getattr(patient, "national_health_id", None)),
    }


def build_batch_claim_pack(
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    visit_ids: list[int] | None = None,
    organization=None,
) -> dict[str, Any]:
    """Build claim packs for multiple visits."""
    qs = Visit.objects.select_related("patient").order_by("-created_at")
    if organization:
        qs = qs.filter(organization=organization)
    if visit_ids:
        qs = qs.filter(id__in=visit_ids)
    else:
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)

    packs = [build_visit_claim_pack(v) for v in qs[:500]]
    claim_ready = [p for p in packs if p["claim_ready"] and p["line_count"] > 0]
    return {
        "visit_count": len(packs),
        "claim_ready_count": len(claim_ready),
        "packs": packs,
    }


def claim_pack_to_csv(packs: list[dict[str, Any]]) -> str:
    """Flatten claim packs to CSV for NHIA/HMO portal upload."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "visit_id",
            "visit_date",
            "patient_mrn",
            "patient_name",
            "national_health_id",
            "nhia_code",
            "icd11",
            "description",
            "amount_ngn",
            "payment_status",
        ]
    )
    for pack in packs:
        for line in pack.get("line_items", []):
            writer.writerow(
                [
                    pack.get("visit_id"),
                    pack.get("visit_date"),
                    pack.get("patient_mrn"),
                    pack.get("patient_name"),
                    pack.get("national_health_id"),
                    line.get("nhia_code"),
                    line.get("icd11"),
                    line.get("description"),
                    line.get("amount_ngn"),
                    pack.get("payment_status"),
                ]
            )
    return output.getvalue()

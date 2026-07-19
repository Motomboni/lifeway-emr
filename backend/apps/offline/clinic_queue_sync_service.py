"""
Execute offline clinic queue entries when connectivity returns.
"""

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .clinic_queue_models import ClinicOfflineQueueEntry

logger = logging.getLogger(__name__)


def _org_matches(entry: ClinicOfflineQueueEntry, org) -> bool:
    if org and entry.organization_id and entry.organization_id != org.id:
        return False
    return True


@transaction.atomic
def execute_offline_queue_entry(
    entry: ClinicOfflineQueueEntry,
    *,
    user,
    organization=None,
) -> dict[str, Any]:
    """Run the queued action and return a result payload."""
    if entry.status != "PENDING":
        raise ValidationError(f"Entry is already {entry.status}.")

    if not _org_matches(entry, organization):
        raise ValidationError("Queue entry does not belong to this organization.")

    payload = entry.payload or {}
    action = entry.action

    if action == "REGISTER_PATIENT":
        result = _sync_register_patient(payload, user=user, organization=organization)
    elif action == "CHECK_IN_VISIT":
        result = _sync_check_in_visit(payload, user=user, organization=organization)
    elif action == "RECORD_VITALS":
        result = _sync_record_vitals(payload, user=user, organization=organization)
    elif action == "QUEUE_NOTE":
        result = {"note": payload.get("note", ""), "acknowledged": True}
    else:
        raise ValidationError(f"Unsupported offline action: {action}")

    entry.status = "SYNCED"
    entry.synced_at = timezone.now()
    entry.error_message = ""
    entry.save(update_fields=["status", "synced_at", "error_message"])
    logger.info("Offline queue entry %s synced (%s)", entry.id, action)
    return result


def _sync_register_patient(payload: dict, *, user, organization) -> dict[str, Any]:
    from apps.patients.models import Patient

    required = ["first_name", "last_name"]
    for field in required:
        if not (payload.get(field) or "").strip():
            raise ValidationError(f"Missing required field: {field}")

    patient = Patient.objects.create(
        first_name=payload["first_name"].strip(),
        last_name=payload["last_name"].strip(),
        middle_name=(payload.get("middle_name") or "").strip(),
        date_of_birth=payload.get("date_of_birth") or None,
        gender=payload.get("gender") or "",
        phone=(payload.get("phone") or "").strip(),
        email=(payload.get("email") or "").strip(),
        address=(payload.get("address") or "").strip(),
        national_id=(payload.get("national_id") or "").strip() or None,
        national_health_id=(payload.get("national_health_id") or "").strip() or None,
        allergies=(payload.get("allergies") or "").strip(),
        organization=organization,
        is_active=True,
    )
    return {"patient_id": patient.id, "patient_number": patient.patient_id}


def _sync_check_in_visit(payload: dict, *, user, organization) -> dict[str, Any]:
    from apps.billing.bill_models import Bill
    from apps.patients.models import Patient
    from apps.visits.models import Visit

    patient_id = payload.get("patient_id")
    if not patient_id:
        raise ValidationError("patient_id is required for CHECK_IN_VISIT.")

    patient = Patient.objects.filter(id=patient_id, is_active=True).first()
    if not patient:
        raise ValidationError("Patient not found.")
    if organization and patient.organization_id != organization.id:
        raise ValidationError("Patient does not belong to this organization.")

    payment_type = payload.get("payment_type") or "CASH"
    if payment_type == "INSURANCE":
        payment_status = "INSURANCE_PENDING"
    else:
        payment_status = payload.get("payment_status") or "UNPAID"

    visit = Visit.objects.create(
        patient=patient,
        visit_type=payload.get("visit_type") or "OUTPATIENT",
        chief_complaint=(payload.get("chief_complaint") or "").strip(),
        status="OPEN",
        payment_type=payment_type,
        payment_status=payment_status,
        organization=organization or patient.organization,
    )
    Bill.objects.get_or_create(
        visit=visit,
        defaults={
            "status": payment_status,
            "created_by": user,
            "is_insurance_backed": payment_type == "INSURANCE",
        },
    )
    return {"visit_id": visit.id, "patient_id": patient.id}


def _sync_record_vitals(payload: dict, *, user, organization) -> dict[str, Any]:
    from apps.clinical.alert_service import AlertSpec, create_clinical_alerts
    from apps.clinical.models import VitalSigns
    from apps.visits.models import Visit

    visit_id = payload.get("visit_id")
    if not visit_id:
        raise ValidationError("visit_id is required for RECORD_VITALS.")

    visit = Visit.objects.filter(id=visit_id).first()
    if not visit:
        raise ValidationError("Visit not found.")
    if organization and visit.organization_id != organization.id:
        raise ValidationError("Visit does not belong to this organization.")
    if visit.status == "CLOSED":
        raise ValidationError("Cannot record vitals for a closed visit.")

    vitals_data = payload.get("vitals") or payload
    allowed_fields = {
        "temperature",
        "systolic_bp",
        "diastolic_bp",
        "pulse",
        "respiratory_rate",
        "oxygen_saturation",
        "weight",
        "height",
        "muac",
        "nutritional_status",
        "urine_anc",
        "lmp",
        "edd",
        "ega_weeks",
        "ega_days",
        "notes",
    }
    create_kwargs = {
        k: vitals_data[k]
        for k in allowed_fields
        if k in vitals_data and vitals_data[k] not in (None, "")
    }

    vital_signs = VitalSigns.objects.create(
        visit=visit,
        recorded_by=user,
        **create_kwargs,
    )

    specs = []
    for flag in vital_signs.get_abnormal_flags():
        severity = (
            "CRITICAL"
            if flag in ["HYPOTENSION", "HYPOXIA", "FEVER"]
            else "HIGH"
        )
        specs.append(
            AlertSpec(
                alert_type="VITAL_SIGNS",
                severity=severity,
                title=f"Abnormal Vital Sign: {flag}",
                message=f"Vital signs recorded show {flag}. Please review.",
                related_resource_type="vital_signs",
                related_resource_id=vital_signs.id,
            )
        )
    create_clinical_alerts(visit, specs)

    return {"vital_signs_id": vital_signs.id, "visit_id": visit.id}


def mark_entry_failed(entry: ClinicOfflineQueueEntry, message: str) -> None:
    entry.status = "FAILED"
    entry.error_message = message[:2000]
    entry.save(update_fields=["status", "error_message"])

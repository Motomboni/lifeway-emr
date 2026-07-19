"""Workflow checklist definitions and auto-detection from visit state."""

from __future__ import annotations

from typing import Any

ROLE_WORKFLOW_PACKS: dict[str, list[str]] = {
    "DOCTOR": ["charting", "close_visit"],
    "NURSE": ["intake"],
    "RECEPTIONIST": ["intake", "close_visit"],
    "ADMIN": ["intake", "charting", "close_visit"],
    "LAB_TECH": ["lab_fulfillment"],
    "PHARMACIST": ["pharmacy_fulfillment"],
}

WORKFLOW_PACKS: dict[str, dict[str, Any]] = {
    "intake": {
        "title": "Intake",
        "steps": [
            {"id": "verify_patient", "label": "Verify patient identity", "guide_target": "patient-summary"},
            {"id": "record_vitals", "label": "Record vitals", "guide_target": "vitals-inline"},
            {"id": "triage_note", "label": "Add triage / nursing note", "guide_target": "nursing-notes"},
            {"id": "assign_doctor", "label": "Queue for doctor", "guide_target": "visit-status"},
        ],
    },
    "charting": {
        "title": "Charting",
        "steps": [
            {"id": "review_alerts", "label": "Review alerts & allergies", "guide_target": "clinical-alerts"},
            {"id": "history_exam", "label": "Document history & exam", "guide_target": "consultation-form"},
            {"id": "diagnosis", "label": "Enter diagnosis", "guide_target": "consultation-form"},
            {"id": "place_orders", "label": "Place orders (lab, Rx, services)", "guide_target": "lab-inline"},
            {"id": "save_consultation", "label": "Save consultation", "guide_target": "consultation-actions"},
        ],
    },
    "close_visit": {
        "title": "Close Visit",
        "steps": [
            {"id": "documentation_complete", "label": "Documentation complete", "guide_target": "consultation-form"},
            {"id": "billing_cleared", "label": "Billing cleared", "guide_target": "billing-dashboard"},
            {"id": "close_visit", "label": "Close visit", "guide_target": "consultation-actions"},
        ],
    },
    "lab_fulfillment": {
        "title": "Lab Fulfillment",
        "steps": [
            {"id": "open_queue", "label": "Open lab worklist", "guide_target": "lab-worklist"},
            {"id": "select_visit", "label": "Select visit with orders", "guide_target": "lab-worklist"},
            {"id": "record_result", "label": "Record lab result", "guide_target": "lab-result-form"},
            {"id": "flag_abnormal", "label": "Flag abnormal results", "guide_target": "lab-result-form"},
        ],
    },
    "pharmacy_fulfillment": {
        "title": "Pharmacy Fulfillment",
        "steps": [
            {"id": "open_queue", "label": "Open prescription queue", "guide_target": "pharmacy-worklist"},
            {"id": "verify_payment", "label": "Verify payment cleared", "guide_target": "pharmacy-worklist"},
            {"id": "dispense", "label": "Dispense medication", "guide_target": "pharmacy-dispense"},
        ],
    },
}


def _has_consultation(visit) -> bool:
    from apps.consultations.models import Consultation

    return Consultation.objects.filter(visit_id=visit.id).exists()


def _has_vitals(visit) -> bool:
    from apps.clinical.models import VitalSigns

    return VitalSigns.objects.filter(visit_id=visit.id).exists()


def _has_lab_order(visit) -> bool:
    from apps.laboratory.models import LabOrder

    return LabOrder.objects.filter(visit_id=visit.id).exists()


def _has_nursing_note(visit) -> bool:
    from apps.nursing.models import NursingNote

    return NursingNote.objects.filter(visit_id=visit.id).exists()


def _has_lab_result(visit) -> bool:
    from apps.laboratory.models import LabOrder, LabResult

    return LabResult.objects.filter(lab_order__visit_id=visit.id).exists()


def _has_abnormal_lab_result(visit) -> bool:
    from apps.laboratory.models import LabResult

    return LabResult.objects.filter(
        lab_order__visit_id=visit.id,
        abnormal_flag__in=["ABNORMAL", "CRITICAL"],
    ).exists()


def _has_prescription(visit) -> bool:
    from apps.pharmacy.models import Prescription

    return Prescription.objects.filter(visit_id=visit.id).exists()


def _has_dispensed_prescription(visit) -> bool:
    from apps.pharmacy.models import Prescription

    return Prescription.objects.filter(visit_id=visit.id, status="DISPENSED").exists()


def detect_completed_steps(visit, pack_id: str) -> list[str]:
    """Infer completed checklist steps from visit-related data."""
    completed: list[str] = []
    if pack_id == "intake":
        if visit.patient_id:
            completed.append("verify_patient")
        if _has_vitals(visit):
            completed.append("record_vitals")
        if _has_nursing_note(visit):
            completed.append("triage_note")
        if _has_consultation(visit) or visit.status == "OPEN":
            completed.append("assign_doctor")
    elif pack_id == "charting":
        completed.append("review_alerts")
        from apps.consultations.models import Consultation

        consultation = Consultation.objects.filter(visit_id=visit.id).first()
        if consultation:
            if consultation.history or consultation.examination:
                completed.append("history_exam")
            if consultation.diagnosis:
                completed.append("diagnosis")
            completed.append("save_consultation")
        if _has_lab_order(visit):
            completed.append("place_orders")
    elif pack_id == "close_visit":
        if _has_consultation(visit):
            completed.append("documentation_complete")
        if visit.payment_status in ("PAID", "SETTLED"):
            completed.append("billing_cleared")
        if visit.status == "CLOSED":
            completed.append("close_visit")
    elif pack_id == "lab_fulfillment":
        if _has_lab_order(visit):
            completed.extend(["open_queue", "select_visit"])
        if _has_lab_result(visit):
            completed.append("record_result")
        if _has_abnormal_lab_result(visit):
            completed.append("flag_abnormal")
    elif pack_id == "pharmacy_fulfillment":
        if _has_prescription(visit):
            completed.append("open_queue")
        if visit.payment_status in ("PAID", "SETTLED"):
            completed.append("verify_payment")
        if _has_dispensed_prescription(visit):
            completed.append("dispense")
    return completed


def build_workflow_response(visit, role: str, stored: dict) -> list[dict]:
    pack_ids = ROLE_WORKFLOW_PACKS.get(role, ["charting"])
    result = []
    for pack_id in pack_ids:
        pack = WORKFLOW_PACKS[pack_id]
        progress = stored.get(pack_id)
        auto_completed = detect_completed_steps(visit, pack_id)
        manual_completed = progress.completed_steps if progress else []
        skipped = progress.skipped_steps if progress else []
        completed = list(dict.fromkeys(auto_completed + manual_completed))
        steps = []
        active_assigned = False
        for step in pack["steps"]:
            step_id = step["id"]
            if step_id in skipped:
                status = "skipped"
            elif step_id in completed:
                status = "completed"
            elif not active_assigned:
                status = "active"
                active_assigned = True
            else:
                status = "pending"
            steps.append({**step, "status": status})
        result.append(
            {
                "pack_id": pack_id,
                "title": pack["title"],
                "steps": steps,
                "completed_count": sum(1 for s in steps if s["status"] == "completed"),
                "total_count": len(steps),
            }
        )
    return result

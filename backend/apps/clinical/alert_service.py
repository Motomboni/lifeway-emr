"""
Automatic clinical alert generation for prescribing and lab results.

Generates ClinicalAlert records for:
- Drug interactions
- Allergy warnings
- Critical / abnormal lab values
- Contraindications
- Dosage warnings
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Iterable

from django.db.models import Q

from apps.clinical.models import ClinicalAlert

if TYPE_CHECKING:
    from apps.laboratory.models import LabResult
    from apps.patients.models import Patient
    from apps.pharmacy.models import Prescription
    from apps.visits.models import Visit

logger = logging.getLogger(__name__)

_SEVERITY_MAP = {
    "Severe": "CRITICAL",
    "Moderate": "HIGH",
    "Mild": "MEDIUM",
}


@dataclass
class AlertSpec:
    alert_type: str
    severity: str
    title: str
    message: str
    related_resource_type: str | None = None
    related_resource_id: int | None = None


def parse_allergy_tokens(allergies_text: str | None) -> list[str]:
    """Split free-text allergies into normalized tokens."""
    if not allergies_text or not str(allergies_text).strip():
        return []
    parts = re.split(r"[,;\n/|]+", str(allergies_text))
    return [p.strip().lower() for p in parts if p.strip()]


def _normalize_name(value: str | None) -> str:
    return (value or "").strip().lower()


def resolve_medication_for_drug(drug_name: str, drug_code: str = ""):
    """Best-effort Medication lookup from prescribed drug text."""
    from apps.pharmacy.models import Drug, Medication

    name = (drug_name or "").strip()
    if not name:
        return None, None

    medication = (
        Medication.objects.filter(is_active=True)
        .filter(Q(name__iexact=name) | Q(generic_name__iexact=name))
        .first()
    )
    if not medication:
        medication = (
            Medication.objects.filter(is_active=True)
            .filter(Q(name__icontains=name) | Q(generic_name__icontains=name))
            .first()
        )

    drug_catalog = None
    if drug_code:
        drug_catalog = Drug.objects.filter(drug_code=drug_code, is_active=True).first()
    if not drug_catalog:
        drug_catalog = Drug.objects.filter(name__iexact=name, is_active=True).first()
    if not drug_catalog and not medication:
        drug_catalog = Drug.objects.filter(name__icontains=name, is_active=True).first()

    if not medication and drug_catalog:
        medication = getattr(drug_catalog, "eprescription_medication", None)

    return medication, drug_catalog


def _medication_ids_for_visit_drugs(visit, exclude_prescription_id: int | None = None) -> list[int]:
    from apps.pharmacy.models import Prescription

    ids: list[int] = []
    qs = Prescription.objects.filter(visit=visit, status="PENDING").exclude(
        status="CANCELLED"
    )
    if exclude_prescription_id:
        qs = qs.exclude(pk=exclude_prescription_id)

    for rx in qs:
        med, _ = resolve_medication_for_drug(rx.drug, rx.drug_code or "")
        if med:
            ids.append(med.id)
    return ids


def get_patient_allergy_tokens(patient: Patient) -> list[str]:
    """Collect allergy tokens from structured records and legacy free text."""
    from apps.patients.allergy_models import PatientAllergy

    tokens: list[str] = []
    seen: set[str] = set()

    for row in PatientAllergy.objects.filter(patient=patient, is_active=True):
        token = _normalize_name(row.allergen)
        if token and token not in seen:
            seen.add(token)
            tokens.append(token)

    for token in parse_allergy_tokens(getattr(patient, "allergies", None)):
        if token not in seen:
            seen.add(token)
            tokens.append(token)

    return tokens


def check_allergy_warnings(
    patient: Patient, drug_name: str, drug_code: str = ""
) -> list[AlertSpec]:
    """Match patient allergies (structured + legacy text) against drug name/class."""
    tokens = get_patient_allergy_tokens(patient)
    if not tokens:
        return []

    medication, drug_catalog = resolve_medication_for_drug(drug_name, drug_code)
    haystacks = [
        _normalize_name(drug_name),
        _normalize_name(getattr(medication, "generic_name", None)),
        _normalize_name(getattr(medication, "name", None)),
        _normalize_name(getattr(medication, "drug_class", None)),
        _normalize_name(getattr(drug_catalog, "generic_name", None)),
        _normalize_name(getattr(drug_catalog, "name", None)),
        _normalize_name(getattr(drug_catalog, "drug_class", None)),
    ]
    haystacks = [h for h in haystacks if h]

    specs: list[AlertSpec] = []
    for token in tokens:
        matched = any(
            token in h or h in token for h in haystacks if len(token) >= 3 or len(h) >= 3
        )
        if matched:
            specs.append(
                AlertSpec(
                    alert_type="ALLERGY",
                    severity="CRITICAL",
                    title=f"Allergy warning: {token.title()}",
                    message=(
                        f"Patient has a documented allergy to '{token}'. "
                        f"Prescribed drug '{drug_name}' may match this allergen. Review before dispensing."
                    ),
                )
            )
            break
    return specs


def check_interaction_warnings(
    visit: Visit,
    drug_name: str,
    drug_code: str = "",
    exclude_prescription_id: int | None = None,
) -> list[AlertSpec]:
    """Detect drug-drug interactions with other pending visit prescriptions."""
    from apps.pharmacy.drug_interaction_service import check_drug_interactions

    medication, _ = resolve_medication_for_drug(drug_name, drug_code)
    if not medication:
        return []

    med_ids = _medication_ids_for_visit_drugs(visit, exclude_prescription_id)
    med_ids.append(medication.id)
    med_ids = list(dict.fromkeys(med_ids))

    if len(med_ids) < 2:
        return []

    specs: list[AlertSpec] = []
    for warning in check_drug_interactions(med_ids):
        if medication.id not in (warning["drug_a_id"], warning["drug_b_id"]):
            continue
        severity = _SEVERITY_MAP.get(warning["severity"], "MEDIUM")
        specs.append(
            AlertSpec(
                alert_type="DRUG_INTERACTION",
                severity=severity,
                title=f"Drug interaction ({warning['severity']})",
                message=warning["message"],
            )
        )
    return specs


def check_contraindication_warnings(
    visit: Visit,
    patient: Patient,
    drug_name: str,
    drug_code: str = "",
) -> list[AlertSpec]:
    """Flag contraindications from medication data vs allergies/diagnosis."""
    medication, drug_catalog = resolve_medication_for_drug(drug_name, drug_code)
    contra_text = ""
    if medication and medication.contraindications:
        contra_text = medication.contraindications
    elif drug_catalog and drug_catalog.description:
        contra_text = drug_catalog.description

    if not contra_text.strip():
        return []

    contra_lower = contra_text.lower()
    specs: list[AlertSpec] = []

    for token in get_patient_allergy_tokens(patient):
        if token in contra_lower:
            specs.append(
                AlertSpec(
                    alert_type="CONTRAINDICATION",
                    severity="CRITICAL",
                    title=f"Contraindication: allergy to {token.title()}",
                    message=(
                        f"'{drug_name}' contraindications mention '{token}'. "
                        "Patient allergy record matches — avoid unless clinically justified."
                    ),
                )
            )

    diagnosis_text = ""
    consultation = getattr(visit, "consultations", None)
    if consultation is not None:
        latest = visit.consultations.order_by("-created_at").first()
        if latest and latest.diagnosis:
            diagnosis_text = latest.diagnosis.lower()

    if diagnosis_text:
        keywords = (
            "pregnancy",
            "pregnant",
            "renal",
            "kidney",
            "hepatic",
            "liver",
            "cardiac",
            "heart failure",
            "asthma",
            "glaucoma",
        )
        for kw in keywords:
            if kw in diagnosis_text and kw in contra_lower:
                specs.append(
                    AlertSpec(
                        alert_type="CONTRAINDICATION",
                        severity="HIGH",
                        title=f"Contraindication: {kw.replace('_', ' ').title()}",
                        message=(
                            f"Patient diagnosis/context mentions '{kw}' and "
                            f"'{drug_name}' lists this in contraindications."
                        ),
                    )
                )
                break

    return specs


def _parse_dose_mg(dosage: str | None) -> float | None:
    if not dosage:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)\s*mg\b", dosage, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    match = re.search(r"(\d+(?:\.\d+)?)", dosage)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def _max_common_dose_mg(drug_catalog) -> float | None:
    if not drug_catalog or not drug_catalog.common_dosages:
        return None
    values = []
    for match in re.finditer(r"(\d+(?:\.\d+)?)\s*mg", drug_catalog.common_dosages, re.I):
        try:
            values.append(float(match.group(1)))
        except ValueError:
            continue
    return max(values) if values else None


def check_dosage_warnings(
    drug_name: str,
    dosage: str,
    drug_code: str = "",
) -> list[AlertSpec]:
    """Warn when prescribed dose exceeds catalog common maximum."""
    _, drug_catalog = resolve_medication_for_drug(drug_name, drug_code)
    prescribed = _parse_dose_mg(dosage)
    max_dose = _max_common_dose_mg(drug_catalog)

    if prescribed is None or max_dose is None:
        return []

    if prescribed <= max_dose:
        return []

    ratio = prescribed / max_dose
    if ratio >= 2:
        severity = "CRITICAL"
    elif ratio >= 1.5:
        severity = "HIGH"
    else:
        severity = "MEDIUM"

    return [
        AlertSpec(
            alert_type="DOSAGE",
            severity=severity,
            title="Dosage above typical range",
            message=(
                f"Prescribed dose ({prescribed:g} mg) exceeds the catalog maximum "
                f"common dose ({max_dose:g} mg) for '{drug_name}'. Verify dosing."
            ),
        )
    ]


def _extract_numeric_values(text: str) -> list[float]:
    values = []
    for match in re.finditer(r"(\d+(?:\.\d+)?)", text or ""):
        try:
            values.append(float(match.group(1)))
        except ValueError:
            continue
    return values


def _catalog_for_test_code(test_code: str):
    from apps.laboratory.catalog_models import LabTestCatalog

    return LabTestCatalog.objects.filter(
        test_code__iexact=test_code.strip(), is_active=True
    ).first()


def _auto_lab_flag(lab_result: LabResult) -> tuple[str | None, str]:
    """
    Evaluate numeric result against catalog reference ranges.
    Returns (severity_or_none, message).
    """
    order = lab_result.lab_order
    tests = order.tests_requested or []
    if not isinstance(tests, list) or not tests:
        return None, ""

    result_values = _extract_numeric_values(lab_result.result_data)
    if not result_values:
        return None, ""

    value = result_values[0]
    test_label = str(tests[0]) if tests else "Lab test"

    catalog = None
    if isinstance(tests[0], dict):
        code = tests[0].get("code") or tests[0].get("test_code") or ""
        test_label = tests[0].get("name") or tests[0].get("test_name") or code
        if code:
            catalog = _catalog_for_test_code(code)
    else:
        catalog = _catalog_for_test_code(str(tests[0]))

    if not catalog or catalog.reference_range_min is None or catalog.reference_range_max is None:
        return None, ""

    try:
        low = float(catalog.reference_range_min)
        high = float(catalog.reference_range_max)
    except (InvalidOperation, TypeError, ValueError):
        return None, ""

    unit = catalog.unit or ""
    if low <= value <= high:
        return None, ""

    span = high - low if high > low else high or 1
    if value < low:
        deviation = (low - value) / span
        direction = "below"
    else:
        deviation = (value - high) / span
        direction = "above"

    severity = "CRITICAL" if deviation >= 0.5 or lab_result.abnormal_flag == "CRITICAL" else "HIGH"
    message = (
        f"{test_label}: {value:g}{(' ' + unit) if unit else ''} is {direction} reference range "
        f"({low:g}–{high:g}{(' ' + unit) if unit else ''})."
    )
    return severity, message


def check_lab_result_warnings(lab_result: LabResult) -> list[AlertSpec]:
    """Generate alerts for critical or auto-detected abnormal lab values."""
    specs: list[AlertSpec] = []

    if lab_result.abnormal_flag == "CRITICAL":
        specs.append(
            AlertSpec(
                alert_type="LAB_CRITICAL",
                severity="CRITICAL",
                title="Critical lab value",
                message=(
                    f"Lab result flagged CRITICAL for order #{lab_result.lab_order_id}: "
                    f"{lab_result.result_data[:500]}"
                ),
                related_resource_type="lab_result",
                related_resource_id=lab_result.id,
            )
        )
    elif lab_result.abnormal_flag == "ABNORMAL":
        specs.append(
            AlertSpec(
                alert_type="LAB_CRITICAL",
                severity="HIGH",
                title="Abnormal lab value",
                message=(
                    f"Lab result flagged ABNORMAL for order #{lab_result.lab_order_id}: "
                    f"{lab_result.result_data[:500]}"
                ),
                related_resource_type="lab_result",
                related_resource_id=lab_result.id,
            )
        )

    auto_severity, auto_message = _auto_lab_flag(lab_result)
    if auto_severity and auto_message:
        if not any(s.alert_type == "LAB_CRITICAL" for s in specs):
            specs.append(
                AlertSpec(
                    alert_type="LAB_CRITICAL",
                    severity=auto_severity,
                    title="Lab value outside reference range",
                    message=auto_message,
                    related_resource_type="lab_result",
                    related_resource_id=lab_result.id,
                )
            )

    return specs


def create_clinical_alert(
    visit: Visit,
    spec: AlertSpec,
    *,
    dedupe: bool = True,
) -> ClinicalAlert | None:
    """Persist one alert, optionally skipping unresolved duplicates."""
    if dedupe:
        exists = ClinicalAlert.objects.filter(
            visit=visit,
            alert_type=spec.alert_type,
            title=spec.title,
            related_resource_type=spec.related_resource_type,
            related_resource_id=spec.related_resource_id,
            is_resolved=False,
        ).exists()
        if exists:
            return None

    return ClinicalAlert.objects.create(
        visit=visit,
        alert_type=spec.alert_type,
        severity=spec.severity,
        title=spec.title,
        message=spec.message,
        related_resource_type=spec.related_resource_type,
        related_resource_id=spec.related_resource_id,
    )


def create_clinical_alerts(
    visit: Visit,
    specs: Iterable[AlertSpec],
) -> list[ClinicalAlert]:
    created: list[ClinicalAlert] = []
    for spec in specs:
        alert = create_clinical_alert(visit, spec)
        if alert:
            created.append(alert)
    return created


def evaluate_prescription_alerts(
    visit: Visit,
    prescription: Prescription,
) -> list[ClinicalAlert]:
    """Run all CDS checks for a new/updated prescription."""
    patient = visit.patient
    drug_name = prescription.drug
    drug_code = prescription.drug_code or ""
    dosage = prescription.dosage or ""

    specs: list[AlertSpec] = []
    specs.extend(check_allergy_warnings(patient, drug_name, drug_code))
    specs.extend(
        check_interaction_warnings(
            visit, drug_name, drug_code, exclude_prescription_id=prescription.pk
        )
    )
    specs.extend(check_contraindication_warnings(visit, patient, drug_name, drug_code))
    specs.extend(check_dosage_warnings(drug_name, dosage, drug_code))

    for spec in specs:
        spec.related_resource_type = "prescription"
        spec.related_resource_id = prescription.id

    alerts = create_clinical_alerts(visit, specs)
    if alerts:
        logger.info(
            "Created %s clinical alert(s) for prescription %s visit %s",
            len(alerts),
            prescription.id,
            visit.id,
        )
    return alerts


def evaluate_lab_result_alerts(
    visit: Visit,
    lab_result: LabResult,
) -> list[ClinicalAlert]:
    """Run lab CDS checks and persist alerts."""
    specs = check_lab_result_warnings(lab_result)
    alerts = create_clinical_alerts(visit, specs)
    if alerts:
        logger.info(
            "Created %s lab alert(s) for result %s visit %s",
            len(alerts),
            lab_result.id,
            visit.id,
        )
    return alerts


def evaluate_eprescription_alerts(
    visit: Visit,
    patient: Patient,
    items: list,
) -> list[ClinicalAlert]:
    """
    Generate alerts for e-prescription items when patient has an open visit.
    items: list of EPrescriptionItem or dicts with medication, dosage.
    """
    specs: list[AlertSpec] = []
    med_ids: list[int] = []

    for item in items:
        medication = getattr(item, "medication", None) or item.get("medication")
        if not medication:
            continue
        med_ids.append(medication.id)
        drug_name = medication.name
        dosage = getattr(item, "dosage", None) or item.get("dosage", "")
        specs.extend(check_allergy_warnings(patient, drug_name))
        specs.extend(check_contraindication_warnings(visit, patient, drug_name))
        specs.extend(check_dosage_warnings(drug_name, dosage or ""))

    if len(med_ids) >= 2:
        from apps.pharmacy.drug_interaction_service import check_drug_interactions

        for warning in check_drug_interactions(med_ids):
            severity = _SEVERITY_MAP.get(warning["severity"], "MEDIUM")
            specs.append(
                AlertSpec(
                    alert_type="DRUG_INTERACTION",
                    severity=severity,
                    title=f"Drug interaction ({warning['severity']})",
                    message=warning["message"],
                    related_resource_type="eprescription",
                )
            )

    return create_clinical_alerts(visit, specs)

"""Tests for automatic clinical alert generation."""

import pytest

from apps.clinical.alert_service import (
    check_allergy_warnings,
    check_dosage_warnings,
    check_interaction_warnings,
    check_lab_result_warnings,
    evaluate_prescription_alerts,
    get_patient_allergy_tokens,
    parse_allergy_tokens,
)
from apps.clinical.models import ClinicalAlert
from apps.laboratory.models import LabOrder, LabResult
from apps.patients.allergy_models import PatientAllergy
from apps.pharmacy.models import Drug, Medication, MedicationInteraction, Prescription


@pytest.mark.django_db
class TestParseAllergyTokens:
    def test_splits_comma_separated(self):
        assert parse_allergy_tokens("Penicillin, Sulfa") == ["penicillin", "sulfa"]


@pytest.mark.django_db
class TestAllergyAlerts:
    def test_allergy_match_creates_spec(self, patient):
        patient.allergies = "Penicillin"
        patient.save()
        specs = check_allergy_warnings(patient, "Amoxicillin (Penicillin class)")
        assert len(specs) == 1
        assert specs[0].alert_type == "ALLERGY"
        assert specs[0].severity == "CRITICAL"

    def test_no_allergy_no_spec(self, patient):
        patient.allergies = ""
        specs = check_allergy_warnings(patient, "Paracetamol")
        assert specs == []

    def test_structured_allergy_match(self, patient, doctor_user):
        PatientAllergy.objects.create(
            patient=patient,
            allergen="Penicillin",
            allergen_type="DRUG",
            severity="SEVERE",
            created_by=doctor_user,
        )
        patient.allergies = ""
        patient.save(update_fields=["allergies"])
        tokens = get_patient_allergy_tokens(patient)
        assert "penicillin" in tokens
        specs = check_allergy_warnings(patient, "Penicillin")
        assert len(specs) == 1


@pytest.mark.django_db
class TestDrugInteractionAlerts:
    def test_interaction_detected(
        self, open_visit_with_payment, consultation, doctor_user
    ):
        med_a = Medication.objects.create(name="Warfarin")
        med_b = Medication.objects.create(name="Aspirin")
        MedicationInteraction.objects.create(
            medication_a=med_a,
            medication_b=med_b,
            severity="Severe",
            description="Increased bleeding risk.",
        )

        Prescription.objects.create(
            visit=open_visit_with_payment,
            consultation=consultation,
            drug="Warfarin",
            dosage="5mg",
            prescribed_by=doctor_user,
        )

        drug = Drug.objects.create(name="Aspirin", created_by=doctor_user)
        Medication.objects.create(name="Aspirin", drug=drug)

        specs = check_interaction_warnings(
            open_visit_with_payment, "Aspirin", exclude_prescription_id=None
        )
        assert len(specs) >= 1
        assert specs[0].alert_type == "DRUG_INTERACTION"
        assert specs[0].severity == "CRITICAL"


@pytest.mark.django_db
class TestDosageAlerts:
    def test_high_dose_warning(self, doctor_user):
        Drug.objects.create(
            name="Paracetamol",
            common_dosages="500mg, 1000mg",
            created_by=doctor_user,
        )
        specs = check_dosage_warnings("Paracetamol", "2000mg twice daily")
        assert len(specs) == 1
        assert specs[0].alert_type == "DOSAGE"


@pytest.mark.django_db
class TestLabCriticalAlerts:
    def test_critical_flag(
        self, open_visit_with_payment, consultation, doctor_user, lab_tech_user
    ):
        order = LabOrder.objects.create(
            visit=open_visit_with_payment,
            consultation=consultation,
            ordered_by=doctor_user,
            tests_requested=["HGB"],
        )
        result = LabResult.objects.create(
            lab_order=order,
            result_data="6.5 g/dL — critically low",
            abnormal_flag="CRITICAL",
            recorded_by=lab_tech_user,
        )
        specs = check_lab_result_warnings(result)
        assert any(s.alert_type == "LAB_CRITICAL" for s in specs)
        assert any(s.severity == "CRITICAL" for s in specs)


@pytest.mark.django_db
class TestEvaluatePrescriptionAlerts:
    def test_persists_alerts(
        self, open_visit_with_payment, consultation, doctor_user, patient
    ):
        patient.allergies = "Amoxicillin"
        patient.save()

        rx = Prescription.objects.create(
            visit=open_visit_with_payment,
            consultation=consultation,
            drug="Amoxicillin",
            dosage="500mg",
            prescribed_by=doctor_user,
        )

        alerts = evaluate_prescription_alerts(open_visit_with_payment, rx)
        assert len(alerts) >= 1
        assert ClinicalAlert.objects.filter(
            visit=open_visit_with_payment, alert_type="ALLERGY"
        ).exists()

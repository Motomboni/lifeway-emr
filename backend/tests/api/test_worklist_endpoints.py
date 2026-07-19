"""Tests for pharmacy and laboratory worklist endpoints."""

import pytest
from rest_framework import status

from apps.laboratory.models import LabOrder
from apps.pharmacy.models import Prescription
from apps.pharmacy.nafdac_models import NAFDACFormularyEntry


@pytest.fixture
def prescription(open_visit_with_payment, consultation, doctor_user):
    return Prescription.objects.create(
        visit=open_visit_with_payment,
        consultation=consultation,
        drug="Amoxicillin",
        dosage="500mg",
        prescribed_by=doctor_user,
        status="PENDING",
    )


@pytest.fixture
def lab_order(open_visit_with_payment, consultation, doctor_user):
    return LabOrder.objects.create(
        visit=open_visit_with_payment,
        consultation=consultation,
        ordered_by=doctor_user,
        tests_requested=["CBC"],
        clinical_indication="Routine check",
        status=LabOrder.Status.ORDERED,
    )


@pytest.fixture
def nafdac_formulary_entry(db):
    return NAFDACFormularyEntry.objects.create(
        nafdac_reg_no="NAFDAC-TEST-001",
        product_name="Test Drug",
        active_ingredient="Paracetamol",
        dosage_form="Tablet",
        strength="500mg",
        manufacturer="Test Pharma",
        is_active=True,
    )


@pytest.mark.django_db
class TestPrescriptionWorklist:
    def test_pharmacist_can_list_prescription_worklist(
        self, api_client, pharmacist_user, test_org, visit, prescription
    ):
        client = api_client(pharmacist_user, test_org)
        response = client.get("/api/v1/drugs/prescriptions/worklist/?status=all")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1
        assert any(row["id"] == visit.id for row in response.data["results"])

    def test_lab_tech_cannot_list_prescription_worklist(
        self, api_client, lab_tech_user, test_org
    ):
        client = api_client(lab_tech_user, test_org)
        response = client.get("/api/v1/drugs/prescriptions/worklist/?status=all")
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestLabOrderWorklist:
    def test_lab_tech_can_list_lab_worklist(
        self, api_client, lab_tech_user, test_org, visit, lab_order
    ):
        client = api_client(lab_tech_user, test_org)
        response = client.get("/api/v1/laboratory/orders/worklist/?status=all")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1
        assert any(row["id"] == visit.id for row in response.data["results"])


@pytest.mark.django_db
class TestNafdacFormularyAccess:
    def test_doctor_can_view_nafdac_formulary(
        self, api_client, doctor_user, test_org, nafdac_formulary_entry
    ):
        client = api_client(doctor_user, test_org)
        response = client.get("/api/v1/pharmacy/nafdac-formulary/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_pharmacist_can_view_nafdac_formulary(
        self, api_client, pharmacist_user, test_org, nafdac_formulary_entry
    ):
        client = api_client(pharmacist_user, test_org)
        response = client.get("/api/v1/pharmacy/nafdac-formulary/")
        assert response.status_code == status.HTTP_200_OK

"""Tests for structured patient allergies API."""

import pytest
from rest_framework import status

from apps.patients.allergy_models import PatientAllergy


@pytest.mark.django_db
class TestPatientAllergyAPI:
    def test_list_and_create_allergy(self, api_client, doctor_user, patient):
        client = api_client(user=doctor_user)
        url = f"/api/v1/patients/{patient.id}/allergies/"

        create_resp = client.post(
            url,
            {
                "allergen": "Penicillin",
                "allergen_type": "DRUG",
                "severity": "SEVERE",
                "reaction": "Rash",
            },
            format="json",
        )
        assert create_resp.status_code == status.HTTP_201_CREATED
        assert create_resp.data["allergen"] == "Penicillin"

        list_resp = client.get(url)
        assert list_resp.status_code == status.HTTP_200_OK
        assert len(list_resp.data) == 1

        patient.refresh_from_db()
        assert "Penicillin" in (patient.allergies or "")

    def test_soft_delete_allergy(self, api_client, doctor_user, patient):
        client = api_client(user=doctor_user)
        allergy = PatientAllergy.objects.create(
            patient=patient,
            allergen="Sulfa",
            allergen_type="DRUG",
            severity="MODERATE",
            created_by=doctor_user,
        )
        url = f"/api/v1/patients/{patient.id}/allergies/{allergy.id}/"
        resp = client.delete(url)
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        allergy.refresh_from_db()
        assert allergy.is_active is False

    def test_nurse_can_add_allergy(self, api_client, nurse_user, patient):
        client = api_client(user=nurse_user)
        url = f"/api/v1/patients/{patient.id}/allergies/"
        resp = client.post(
            url,
            {"allergen": "Peanuts", "allergen_type": "FOOD"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED

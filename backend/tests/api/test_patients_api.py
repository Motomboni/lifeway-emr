"""
Comprehensive API tests for Patient endpoints.
Tests CRUD operations, search, and permissions.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.patients.models import Patient


@pytest.mark.django_db
class TestPatientSearchAPI:
    """Test patient search functionality."""

    def test_search_patients_by_name(self, receptionist_token, test_org, api_client):
        """Test searching patients by name."""
        client = api_client(token=receptionist_token)

        # Create test patient
        Patient.objects.create(
            first_name="John",
            last_name="Doe",
            patient_id="PAT001",
            organization=test_org,
        )

        response = client.get("/api/v1/patients/?search=John")

        assert response.status_code == status.HTTP_200_OK

    def test_search_patients_by_id(self, receptionist_token, test_org, api_client):
        """Test searching patients by patient ID."""
        client = api_client(token=receptionist_token)

        Patient.objects.create(
            first_name="Jane",
            last_name="Smith",
            patient_id="PAT002",
            organization=test_org,
        )

        response = client.get("/api/v1/patients/?search=PAT002")

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestPatientCreateAPI:
    """Test patient creation."""

    def test_create_patient_receptionist(self, receptionist_token, api_client):
        """Test receptionist can create patient."""
        client = api_client(token=receptionist_token)

        data = {
            "first_name": "Test",
            "last_name": "Patient",
            "date_of_birth": "1990-01-01",
            "gender": "MALE",
            "phone": "1234567890",
        }

        response = client.post("/api/v1/patients/", data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["success"] is True
        assert response.data["patient"]["first_name"] == "Test"

    def test_create_patient_duplicate_national_id(self, receptionist_token, api_client):
        """Test creating patient with duplicate national ID."""
        client = api_client(token=receptionist_token)

        # Create first patient
        Patient.objects.create(
            first_name="First", last_name="Patient", national_id="NID123"
        )

        # Try to create duplicate
        data = {"first_name": "Second", "last_name": "Patient", "national_id": "NID123"}

        response = client.post("/api/v1/patients/", data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestPatientPermissionsAPI:
    """Ensure PATIENT role cannot access staff patient endpoints."""

    def test_patient_cannot_list_patients(self, patient_token, api_client):
        client = api_client(token=patient_token)

        response = client.get("/api/v1/patients/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_patient_cannot_retrieve_other_patient(self, patient_token, patient, api_client):
        client = api_client(token=patient_token)

        response = client.get(f"/api/v1/patients/{patient.id}/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_doctor_can_list_patients(self, doctor_token, api_client):
        client = api_client(token=doctor_token)

        response = client.get("/api/v1/patients/")

        assert response.status_code == status.HTTP_200_OK

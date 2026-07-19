"""Patient portal immunization schedule access."""

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestPatientPortalImmunizations:
    def test_verified_patient_can_view_own_immunizations(
        self, api_client, verified_patient
    ):
        from apps.clinical.immunization_models import ImmunizationRecord
        from rest_framework_simplejwt.tokens import RefreshToken

        ImmunizationRecord.objects.create(
            patient=verified_patient,
            vaccine="BCG",
            dose_number=1,
            scheduled_date="2026-01-10",
            administered_date="2026-01-10",
        )

        token = str(RefreshToken.for_user(verified_patient.user).access_token)
        client = api_client(token=token)
        response = client.get("/api/v1/patient-portal/immunizations/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["vaccine"] == "BCG"

    def test_patient_cannot_view_other_patient_immunizations_via_portal(
        self, api_client, verified_patient, test_org
    ):
        from apps.clinical.immunization_models import ImmunizationRecord
        from apps.patients.models import Patient
        from rest_framework_simplejwt.tokens import RefreshToken

        # verified_patient is built from the shared `patient` fixture, so use a
        # distinct record to assert patients cannot see another person's doses.
        other_patient = Patient.objects.create(
            first_name="Other",
            last_name="Patient",
            patient_id="OTHER001",
            is_active=True,
            organization=test_org,
        )
        ImmunizationRecord.objects.create(
            patient=other_patient,
            vaccine="OPV",
            dose_number=1,
            scheduled_date="2026-02-01",
        )

        token = str(RefreshToken.for_user(verified_patient.user).access_token)
        client = api_client(token=token)
        response = client.get("/api/v1/patient-portal/immunizations/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_staff_cannot_access_patient_portal_immunizations(
        self, api_client, doctor_token
    ):
        client = api_client(token=doctor_token)
        response = client.get("/api/v1/patient-portal/immunizations/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

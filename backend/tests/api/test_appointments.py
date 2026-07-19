"""Appointment API tests — doctor self-scheduling and receptionist visibility."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status

User = get_user_model()


@pytest.mark.django_db
class TestDoctorAppointments:
    def test_doctor_can_schedule_own_appointment(
        self, api_client, doctor_user, patient, test_org
    ):
        client = api_client(user=doctor_user)
        appointment_date = (timezone.now() + timedelta(days=2)).replace(
            microsecond=0
        ).isoformat()

        response = client.post(
            "/api/v1/appointments/",
            {
                "patient": patient.id,
                "doctor": doctor_user.id,
                "appointment_date": appointment_date,
                "duration_minutes": 30,
                "reason": "Follow-up review",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["doctor"] == doctor_user.id

        detail = client.get(f"/api/v1/appointments/{response.data['id']}/")
        assert detail.status_code == status.HTTP_200_OK
        assert detail.data["created_by"] == doctor_user.id

    def test_doctor_cannot_schedule_for_another_doctor(
        self, api_client, doctor_user, patient, test_org, db
    ):
        other = User(username="otherdoc", email="other@test.com", role="DOCTOR")
        other.set_password("testpass123")
        other.save()

        client = api_client(user=doctor_user)
        appointment_date = (timezone.now() + timedelta(days=2)).replace(
            microsecond=0
        ).isoformat()

        response = client.post(
            "/api/v1/appointments/",
            {
                "patient": patient.id,
                "doctor": other.id,
                "appointment_date": appointment_date,
                "duration_minutes": 30,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["doctor"] == doctor_user.id

    def test_receptionist_sees_doctor_scheduled_appointment(
        self, api_client, doctor_user, receptionist_user, patient, test_org
    ):
        doctor_client = api_client(user=doctor_user)
        appointment_date = (timezone.now() + timedelta(days=3)).replace(
            microsecond=0
        ).isoformat()

        create_response = doctor_client.post(
            "/api/v1/appointments/",
            {
                "patient": patient.id,
                "doctor": doctor_user.id,
                "appointment_date": appointment_date,
                "duration_minutes": 45,
                "reason": "ANC visit",
            },
            format="json",
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        appointment_id = create_response.data["id"]

        reception_client = api_client(user=receptionist_user)
        list_response = reception_client.get("/api/v1/appointments/")
        assert list_response.status_code == status.HTTP_200_OK

        results = (
            list_response.data["results"]
            if isinstance(list_response.data, dict)
            else list_response.data
        )
        ids = [item["id"] for item in results]
        assert appointment_id in ids

        match = next(item for item in results if item["id"] == appointment_id)
        assert match["created_by"] == doctor_user.id
        assert match["doctor"] == doctor_user.id

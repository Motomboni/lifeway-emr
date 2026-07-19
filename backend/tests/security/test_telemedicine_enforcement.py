"""Security tests for telemedicine payment gates and recording access."""

import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone
from rest_framework import status

from apps.billing.billing_line_item_models import BillingLineItem
from apps.billing.service_catalog_models import ServiceCatalog
from apps.telemedicine.models import TelemedicineSession
from apps.visits.models import Visit


def get_response_data(response):
    if hasattr(response, "data"):
        return response.data
    return json.loads(response.content.decode())


@pytest.fixture
def visit_reg_paid_only(patient, test_org):
    """Visit with registration paid but consultation still due."""
    visit = Visit.objects.create(
        patient=patient,
        organization=test_org,
        status="OPEN",
        payment_status="PARTIALLY_PAID",
    )
    reg_service = ServiceCatalog.objects.create(
        organization=test_org,
        service_code="REG-TEST",
        name="REGISTRATION",
        department="PROCEDURE",
        workflow_type="OTHER",
        category="PROCEDURE",
        amount=Decimal("5000.00"),
        is_active=True,
        allowed_roles=["RECEPTIONIST", "DOCTOR"],
    )
    cons_service = ServiceCatalog.objects.create(
        organization=test_org,
        service_code="CONS-TEST",
        name="GOPD CONSULTATION",
        department="CONSULTATION",
        workflow_type="GOPD_CONSULT",
        category="CONSULTATION",
        amount=Decimal("15000.00"),
        is_active=True,
        allowed_roles=["RECEPTIONIST", "DOCTOR"],
    )
    reg_item = BillingLineItem.objects.create(
        service_catalog=reg_service,
        visit=visit,
        source_service_code=reg_service.service_code,
        source_service_name=reg_service.name,
        amount=reg_service.amount,
    )
    reg_item.amount_paid = reg_item.amount
    reg_item.save()
    BillingLineItem.objects.create(
        service_catalog=cons_service,
        visit=visit,
        source_service_code=cons_service.service_code,
        source_service_name=cons_service.name,
        amount=cons_service.amount,
    )
    return visit


@pytest.fixture
def telemedicine_session(unpaid_visit, doctor_user, patient_with_user):
    return TelemedicineSession.objects.create(
        visit=unpaid_visit,
        doctor=doctor_user,
        patient=patient_with_user,
        twilio_room_sid="RM_test_unpaid",
        twilio_room_name="room-unpaid-test",
        status="SCHEDULED",
        scheduled_start=timezone.now(),
        created_by=doctor_user,
    )


@pytest.fixture
def telemedicine_session_reg_paid(visit_reg_paid_only, doctor_user, patient_with_user):
    return TelemedicineSession.objects.create(
        visit=visit_reg_paid_only,
        doctor=doctor_user,
        patient=patient_with_user,
        twilio_room_sid="RM_test_reg_paid",
        twilio_room_name="room-reg-paid-test",
        status="IN_PROGRESS",
        scheduled_start=timezone.now(),
        created_by=doctor_user,
    )


@pytest.fixture
def paid_telemedicine_session(open_visit_with_payment, doctor_user, patient_with_user):
    return TelemedicineSession.objects.create(
        visit=open_visit_with_payment,
        doctor=doctor_user,
        patient=patient_with_user,
        twilio_room_sid="RM_test_paid",
        twilio_room_name="room-paid-test",
        status="IN_PROGRESS",
        scheduled_start=timezone.now(),
        created_by=doctor_user,
    )


@pytest.mark.django_db
class TestTelemedicinePaymentGates:
    @patch("apps.telemedicine.views.create_video_room")
    def test_create_session_blocked_without_registration_payment(
        self, mock_room, api_client, doctor_user, unpaid_visit
    ):
        mock_room.return_value = {
            "room_sid": "RM_new",
            "room_name": "room-new",
        }
        client = api_client(user=doctor_user)
        response = client.post(
            "/api/v1/telemedicine/",
            {
                "visit": unpaid_visit.id,
                "scheduled_start": timezone.now().isoformat(),
                "recording_enabled": False,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "registration" in str(get_response_data(response)).lower()

    def test_join_token_blocked_for_doctor_without_consultation_payment(
        self, api_client, doctor_user, telemedicine_session_reg_paid
    ):
        client = api_client(user=doctor_user)
        response = client.post(
            "/api/v1/telemedicine/token/",
            {"session_id": telemedicine_session_reg_paid.id},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "consultation" in str(get_response_data(response)).lower()

    @patch("apps.telemedicine.views.generate_video_access_token")
    def test_patient_join_blocked_without_registration_payment(
        self, mock_token, api_client, patient_with_user, telemedicine_session
    ):
        mock_token.return_value = "fake-token"
        client = api_client(user=patient_with_user.user)
        response = client.get(
            f"/api/v1/telemedicine/{telemedicine_session.id}/join/",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "registration" in str(get_response_data(response)).lower()


@pytest.mark.django_db
class TestTelemedicineRecordingAuth:
    def test_recording_denied_for_unrelated_user(
        self, api_client, nurse_user, paid_telemedicine_session
    ):
        paid_telemedicine_session.recording_sid = "RE_test123"
        paid_telemedicine_session.save(update_fields=["recording_sid"])

        client = api_client(user=nurse_user)
        response = client.get(
            f"/api/v1/telemedicine/{paid_telemedicine_session.id}/recording/",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("requests.get")
    def test_recording_allowed_for_session_doctor(
        self, mock_get, api_client, doctor_user, paid_telemedicine_session
    ):
        paid_telemedicine_session.recording_sid = "RE_test123"
        paid_telemedicine_session.save(update_fields=["recording_sid"])

        media_resp = MagicMock()
        media_resp.status_code = 302
        media_resp.headers = {"Location": "https://media.example/recording.mp4"}

        stream_resp = MagicMock()
        stream_resp.headers = {"Content-Type": "video/mp4"}
        stream_resp.iter_content = lambda chunk_size: [b"video-data"]
        stream_resp.raise_for_status = lambda: None

        mock_get.side_effect = [media_resp, stream_resp]

        client = api_client(user=doctor_user)
        response = client.get(
            f"/api/v1/telemedicine/{paid_telemedicine_session.id}/recording/",
        )
        assert response.status_code == status.HTTP_200_OK

        from core.audit import AuditLog

        assert AuditLog.objects.filter(
            action="TELEMEDICINE_RECORDING_VIEWED",
            resource_id=str(paid_telemedicine_session.id),
        ).exists()

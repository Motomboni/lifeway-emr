"""Tests for virtual clinic staff invites."""

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.telemedicine.models import TelemedicineParticipant, TelemedicineSession


@pytest.fixture
def tele_session(db, doctor_user, patient_with_user):
    from apps.visits.models import Visit

    visit = Visit.objects.create(
        patient=patient_with_user,
        organization=getattr(patient_with_user, "organization", None),
        status="OPEN",
        payment_status="PAID",
    )
    return TelemedicineSession.objects.create(
        visit=visit,
        doctor=doctor_user,
        patient=patient_with_user,
        twilio_room_sid="RM_clinic_test",
        twilio_room_name="room-clinic-test",
        status="IN_PROGRESS",
        scheduled_start=timezone.now(),
        created_by=doctor_user,
        video_provider="livekit",
    )


@pytest.mark.django_db
def test_doctor_can_invite_nurse(tele_session, doctor_user, nurse_user):
    client = APIClient()
    client.force_authenticate(user=doctor_user)
    resp = client.post(
        f"/api/v1/telemedicine/{tele_session.id}/invite/",
        {"user_id": nurse_user.id, "clinic_role": "NURSE", "message": "Need vitals"},
        format="json",
    )
    assert resp.status_code in (200, 201), resp.content
    data = resp.json()
    assert data["clinic_role"] == "NURSE"
    assert data["invite_status"] == "PENDING"
    assert TelemedicineParticipant.objects.filter(
        session=tele_session, user=nurse_user, invite_status="PENDING"
    ).exists()


@pytest.mark.django_db
def test_nurse_sees_invited_session(tele_session, doctor_user, nurse_user):
    TelemedicineParticipant.objects.create(
        session=tele_session,
        user=nurse_user,
        clinic_role="NURSE",
        invite_status="PENDING",
        invited_by=doctor_user,
        invited_at=timezone.now(),
    )
    client = APIClient()
    client.force_authenticate(user=nurse_user)
    resp = client.get("/api/v1/telemedicine/")
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()]
    assert tele_session.id in ids


@pytest.mark.django_db
def test_nurse_can_accept_and_get_token(tele_session, doctor_user, nurse_user, monkeypatch):
    TelemedicineParticipant.objects.create(
        session=tele_session,
        user=nurse_user,
        clinic_role="NURSE",
        invite_status="PENDING",
        invited_by=doctor_user,
        invited_at=timezone.now(),
    )
    monkeypatch.setattr(
        "apps.telemedicine.views.generate_video_access_token",
        lambda **kwargs: "test-token",
    )
    monkeypatch.setattr(
        "apps.telemedicine.views.resolve_session_video_provider",
        lambda session: "livekit",
    )
    monkeypatch.setattr(
        "apps.telemedicine.views.get_public_video_config",
        lambda provider: {"livekit_url": "ws://localhost:7880"},
    )
    monkeypatch.setattr(
        "apps.telemedicine.views.enforce_telemedicine_payment_gates",
        lambda *a, **k: None,
    )

    client = APIClient()
    client.force_authenticate(user=nurse_user)
    accept = client.post(
        f"/api/v1/telemedicine/{tele_session.id}/respond-invite/",
        {"accept": True},
        format="json",
    )
    assert accept.status_code == 200
    assert accept.json()["invite_status"] == "ACCEPTED"

    token = client.post(
        "/api/v1/telemedicine/token/",
        {"session_id": tele_session.id},
        format="json",
    )
    assert token.status_code == 200
    assert token.json()["token"] == "test-token"

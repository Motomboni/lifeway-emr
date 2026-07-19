"""Telemedicine patient/staff notifications and meeting links."""

from django.conf import settings

from apps.notifications.nigeria_comms import send_telemedicine_invite_sms
from apps.notifications.sms_utils import send_sms_notification


def build_meeting_link(session_id: int) -> str:
    base_url = getattr(settings, "FRONTEND_URL", "").rstrip("/")
    if base_url:
        return f"{base_url}/telemedicine/room/{session_id}"
    return ""


def notify_patient_telemedicine_invite(session, *, created_by=None, event: str = "created"):
    """Best-effort SMS invite when a session is created or started."""
    if not getattr(settings, "SMS_ENABLED", False):
        return None
    link = build_meeting_link(session.id)
    if not link:
        return None
    doctor = session.doctor
    doctor_name = ""
    if doctor:
        doctor_name = f"{doctor.first_name} {doctor.last_name}".strip()
    return send_telemedicine_invite_sms(
        patient=session.patient,
        meeting_link=link,
        visit=session.visit,
        doctor_name=doctor_name,
        created_by=created_by,
    )


def notify_staff_telemedicine_invite(
    session,
    invitee,
    *,
    created_by=None,
    clinic_role: str = "",
    message: str = "",
):
    """Best-effort SMS when clinical staff are invited into a virtual clinic."""
    if not getattr(settings, "SMS_ENABLED", False):
        return None
    phone = (getattr(invitee, "phone", None) or "").strip()
    if not phone:
        return None
    link = build_meeting_link(session.id)
    doctor = session.doctor
    doctor_name = ""
    if doctor:
        doctor_name = f"{doctor.first_name} {doctor.last_name}".strip()
    patient_name = ""
    if session.patient:
        patient_name = session.patient.get_full_name() or f"Visit #{session.visit_id}"
    clinic = getattr(settings, "CLINIC_NAME", "Lifeway Medical Centre")
    role_part = f" as {clinic_role.lower()}" if clinic_role else ""
    note = f" Note: {message}" if message else ""
    join_part = f" Join: {link}" if link else " Open Virtual Clinic in the EMR to join."
    sms = (
        f"{clinic}: Dr. {doctor_name or 'Host'} invited you{role_part} "
        f"to a virtual clinic for {patient_name}.{note}{join_part}"
    )
    return send_sms_notification(
        phone,
        sms,
        notification_type="SYSTEM_ALERT",
        visit=session.visit,
        created_by=created_by,
    )

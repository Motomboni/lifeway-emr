"""
Unified Nigeria patient communications — Termii SMS, payment links, results alerts.
"""

from __future__ import annotations

import logging

from django.conf import settings

from apps.notifications.sms_utils import send_sms_notification

logger = logging.getLogger(__name__)


def send_patient_sms(
    phone: str,
    message: str,
    *,
    notification_type: str = "SYSTEM_ALERT",
    visit=None,
    appointment=None,
    created_by=None,
):
    """Send SMS via configured provider (Termii preferred in production)."""
    if not phone or not phone.strip():
        return None
    return send_sms_notification(
        phone_number=phone.strip(),
        message=message,
        notification_type=notification_type,
        visit=visit,
        appointment=appointment,
        created_by=created_by,
    )


def send_otp_sms(phone: str, otp_code: str, *, created_by=None):
    clinic = getattr(settings, "CLINIC_NAME", "Lifeway Medical Centre")
    message = f"{clinic}: Your login code is {otp_code}. Valid for 5 minutes. Do not share."
    return send_patient_sms(
        phone,
        message,
        notification_type="OTP",
        created_by=created_by,
    )


def send_appointment_reminder_sms(appointment, *, created_by=None):
    patient = appointment.patient
    phone = patient.phone or ""
    if not phone:
        return None
    clinic = getattr(settings, "CLINIC_NAME", "Lifeway Medical Centre")
    when = appointment.appointment_date.strftime("%d %b %Y %H:%M")
    message = (
        f"{clinic}: Reminder — appointment on {when}. "
        f"Reply or call {getattr(settings, 'CLINIC_PHONE', '')} to reschedule."
    )
    return send_patient_sms(
        phone,
        message,
        notification_type="APPOINTMENT_REMINDER",
        appointment=appointment,
        created_by=created_by,
    )


def send_lab_result_ready_sms(*, patient, visit=None, created_by=None):
    phone = getattr(patient, "phone", "") or ""
    if not phone:
        return None
    clinic = getattr(settings, "CLINIC_NAME", "Lifeway Medical Centre")
    portal = getattr(settings, "FRONTEND_URL", "").rstrip("/")
    message = (
        f"{clinic}: Your lab results are ready. "
        f"{'Sign in at ' + portal if portal else 'Visit the clinic or patient portal'}."
    )
    return send_patient_sms(
        phone,
        message,
        notification_type="LAB_RESULT_READY",
        visit=visit,
        created_by=created_by,
    )


def send_paystack_payment_link_sms(*, patient, amount_ngn: str, payment_url: str, visit=None, created_by=None):
    phone = getattr(patient, "phone", "") or ""
    if not phone:
        return None
    clinic = getattr(settings, "CLINIC_NAME", "Lifeway Medical Centre")
    message = f"{clinic}: Pay ₦{amount_ngn} securely: {payment_url}"
    return send_patient_sms(
        phone,
        message,
        notification_type="PAYMENT_LINK",
        visit=visit,
        created_by=created_by,
    )


def send_telemedicine_invite_sms(
    *,
    patient,
    meeting_link: str,
    visit=None,
    doctor_name: str = "",
    created_by=None,
):
    """SMS patient a telemedicine join link (Termii when configured)."""
    phone = getattr(patient, "phone", "") or ""
    if not phone or not meeting_link:
        return None
    clinic = getattr(settings, "CLINIC_NAME", "Lifeway Medical Centre")
    doctor_part = f" with Dr. {doctor_name}" if doctor_name else ""
    message = (
        f"{clinic}: Your video consultation{doctor_part} is ready. "
        f"Join securely: {meeting_link}"
    )
    return send_patient_sms(
        phone,
        message,
        notification_type="TELEMEDICINE_INVITE",
        visit=visit,
        created_by=created_by,
    )

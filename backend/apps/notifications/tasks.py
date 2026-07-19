"""
Celery tasks for patient notifications (SMS / email / WhatsApp).
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="apps.notifications.tasks.send_appointment_reminder_batch")
def send_appointment_reminder_batch(hours_ahead=24):
    """Send appointment reminders (email + SMS) for upcoming appointments."""
    from apps.appointments.models import Appointment
    from apps.notifications.utils import send_appointment_reminder

    now = timezone.now()
    reminder_time = now + timedelta(hours=hours_ahead)

    appointments = Appointment.objects.filter(
        status__in=["SCHEDULED", "CONFIRMED"],
        appointment_date__gte=now,
        appointment_date__lte=reminder_time,
    ).select_related("patient", "doctor")

    sent = 0
    for appointment in appointments:
        patient = appointment.patient
        if not patient or not (patient.email or patient.phone):
            continue
        try:
            send_appointment_reminder(appointment)
            sent += 1
        except Exception as e:
            logger.exception(
                "Appointment reminder failed for #%s: %s", appointment.id, e
            )

    logger.info("Appointment reminders sent: %s", sent)
    return sent


def _whatsapp_appointment_window(hours_ahead: int, window_hours: float = 1.0):
    """Appointments starting within [now+hours_ahead, now+hours_ahead+window]."""
    from apps.appointments.models import Appointment
    from apps.notifications.models import AppointmentReminder
    from apps.notifications.whatsapp_service import send_whatsapp_message

    now = timezone.now()
    start = now + timedelta(hours=hours_ahead)
    end = start + timedelta(hours=window_hours)
    sent = 0

    appointments = Appointment.objects.filter(
        status__in=["SCHEDULED", "CONFIRMED"],
        appointment_date__gte=start,
        appointment_date__lt=end,
    ).select_related("patient")

    for appt in appointments:
        patient = appt.patient
        if not patient or not patient.phone:
            continue
        if AppointmentReminder.objects.filter(
            appointment=appt,
            channel="whatsapp",
            hours_before=hours_ahead,
            status="SENT",
        ).exists():
            continue
        when = appt.appointment_date.strftime("%d %b %Y %H:%M")
        message = (
            f"Hello {patient.first_name or 'there'}, reminder from Lifeway Medical Centre: "
            f"your appointment is on {when}. Please arrive 15 minutes early."
        )
        reminder = AppointmentReminder.objects.create(
            appointment=appt,
            channel="whatsapp",
            hours_before=hours_ahead,
            status="PENDING",
        )
        if send_whatsapp_message(patient.phone, message):
            reminder.status = "SENT"
            reminder.sent_at = timezone.now()
            reminder.save(update_fields=["status", "sent_at"])
            sent += 1
        else:
            reminder.status = "FAILED"
            reminder.error_message = "WhatsApp send failed"
            reminder.save(update_fields=["status", "error_message"])
    return sent


def run_whatsapp_reminders_24h() -> int:
    return _whatsapp_appointment_window(hours_ahead=24)


def run_whatsapp_reminders_2h() -> int:
    return _whatsapp_appointment_window(hours_ahead=2)


@shared_task(name="apps.notifications.tasks.send_whatsapp_reminder_batch")
def send_whatsapp_reminder_batch():
    """Run 24h and 2h WhatsApp appointment reminders."""
    s24 = run_whatsapp_reminders_24h()
    s2 = run_whatsapp_reminders_2h()
    return {"24h": s24, "2h": s2}


@shared_task(name="apps.notifications.tasks.send_anc_whatsapp_reminders")
def send_anc_whatsapp_reminders():
    """Send WhatsApp reminders for due/overdue ANC schedule items."""
    from datetime import date

    from apps.antenatal.models import AntenatalRecord
    from apps.antenatal.schedule_service import (
        build_anc_schedule,
        format_anc_whatsapp_reminder,
    )
    from apps.notifications.whatsapp_service import send_whatsapp_message

    today = date.today()
    sent = 0
    records = AntenatalRecord.objects.filter(outcome="ONGOING").select_related(
        "patient"
    )[:200]

    for record in records:
        patient = record.patient
        if not patient or not patient.phone:
            continue
        schedule = build_anc_schedule(record)
        due_items = [
            i
            for i in schedule.get("items", [])
            if i["status"] in ("due", "overdue")
            and abs(
                (
                    date.fromisoformat(i["due_date"]) - today
                ).days
            )
            <= 3
        ]
        if not due_items:
            continue
        item = due_items[0]
        message = format_anc_whatsapp_reminder(record, item)
        if send_whatsapp_message(patient.phone, message):
            sent += 1

    logger.info("ANC WhatsApp reminders sent: %s", sent)
    return sent

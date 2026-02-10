"""
Background tasks for appointment reminders (24h and 2h before).

Run via:
- Cron: python manage.py send_whatsapp_reminders
- Or Celery Beat if CELERY_APP is configured (see below).
"""
import logging
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)

# Template for reminder message (Nigeria-friendly)
REMINDER_TEMPLATE = (
    "Reminder: You have an appointment at {clinic} on {date} at {time}. "
    "Reply HELP if you need assistance."
)


def _get_clinic_name():
    """Clinic name for messages (from settings or default)."""
    from django.conf import settings
    return getattr(settings, 'CLINIC_NAME', 'the clinic')


def _format_phone(patient):
    """Get E.164-style phone for WhatsApp (e.g. +2348012345678)."""
    phone = (patient.phone or getattr(patient.user, 'phone', None) or '').strip()
    if not phone:
        return None
    if not phone.startswith('+'):
        # Nigerian: assume 0xx -> +234xx
        if phone.startswith('0') and len(phone) >= 10:
            phone = '+234' + phone[1:]
        else:
            phone = '+234' + phone
    return phone


def send_reminder_for_appointment(appointment, hours_before):
    """
    Send one reminder for an appointment (24h or 2h before).
    Creates AppointmentReminder record and calls WhatsApp stub.
    """
    from apps.notifications.models import AppointmentReminder
    from apps.notifications.whatsapp_service import send_whatsapp_message
    
    patient = appointment.patient
    phone = _format_phone(patient)
    if not phone:
        logger.warning("No phone for patient %s, skip WhatsApp reminder", patient.id)
        return False
    
    clinic = _get_clinic_name()
    apt_date = appointment.appointment_date
    date_str = apt_date.strftime('%A, %d %B %Y')
    time_str = apt_date.strftime('%I:%M %p')
    message = REMINDER_TEMPLATE.format(
        clinic=clinic,
        date=date_str,
        time=time_str,
    )
    
    reminder = AppointmentReminder.objects.create(
        appointment=appointment,
        channel='whatsapp',
        hours_before=hours_before,
        status='PENDING',
    )
    try:
        ok = send_whatsapp_message(phone, message)
        reminder.sent_at = timezone.now()
        reminder.status = 'SENT' if ok else 'FAILED'
        if not ok:
            reminder.error_message = 'Send failed (stub or provider error)'
        reminder.save()
        return ok
    except Exception as e:
        reminder.status = 'FAILED'
        reminder.error_message = str(e)
        reminder.save()
        logger.exception("WhatsApp reminder failed for appointment %s: %s", appointment.id, e)
        return False


def run_whatsapp_reminders_24h():
    """Find appointments in the 24h window and send reminders (if not already sent)."""
    from apps.appointments.models import Appointment
    from apps.notifications.models import AppointmentReminder
    
    now = timezone.now()
    window_start = now + timedelta(hours=23)
    window_end = now + timedelta(hours=25)
    
    appointments = Appointment.objects.filter(
        status__in=['SCHEDULED', 'CONFIRMED'],
        appointment_date__gte=window_start,
        appointment_date__lte=window_end,
    ).select_related('patient')
    
    sent = 0
    for apt in appointments:
        if AppointmentReminder.objects.filter(appointment=apt, hours_before=24, channel='whatsapp').exists():
            continue
        if send_reminder_for_appointment(apt, hours_before=24):
            sent += 1
    return sent


def run_whatsapp_reminders_2h():
    """Find appointments in the 2h window and send reminders (if not already sent)."""
    from apps.appointments.models import Appointment
    from apps.notifications.models import AppointmentReminder
    
    now = timezone.now()
    window_start = now + timedelta(hours=1, minutes=50)
    window_end = now + timedelta(hours=2, minutes=10)
    
    appointments = Appointment.objects.filter(
        status__in=['SCHEDULED', 'CONFIRMED'],
        appointment_date__gte=window_start,
        appointment_date__lte=window_end,
    ).select_related('patient')
    
    sent = 0
    for apt in appointments:
        if AppointmentReminder.objects.filter(appointment=apt, hours_before=2, channel='whatsapp').exists():
            continue
        if send_reminder_for_appointment(apt, hours_before=2):
            sent += 1
    return sent

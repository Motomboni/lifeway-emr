"""
Celery tasks for patient notifications (SMS / email).
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

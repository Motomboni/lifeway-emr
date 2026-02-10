"""
Management command to send appointment reminders.

Usage:
    python manage.py send_appointment_reminders

This command should be run periodically (e.g., via cron) to send
reminder emails for upcoming appointments.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.appointments.models import Appointment
from apps.notifications.utils import send_appointment_reminder


class Command(BaseCommand):
    help = 'Send appointment reminder emails for appointments scheduled in the next 24 hours'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Number of hours ahead to send reminders (default: 24)',
        )

    def handle(self, *args, **options):
        hours_ahead = options['hours']
        now = timezone.now()
        reminder_time = now + timedelta(hours=hours_ahead)
        
        # Find appointments scheduled within the reminder window
        appointments = Appointment.objects.filter(
            status__in=['SCHEDULED', 'CONFIRMED'],
            appointment_date__gte=now,
            appointment_date__lte=reminder_time,
        ).select_related('patient', 'doctor')
        
        sent_count = 0
        failed_count = 0
        
        for appointment in appointments:
            try:
                if appointment.patient and appointment.patient.email:
                    send_appointment_reminder(appointment)
                    sent_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Sent reminder for appointment #{appointment.id} '
                            f'({appointment.patient.get_full_name()})'
                        )
                    )
            except Exception as e:
                failed_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'Failed to send reminder for appointment #{appointment.id}: {e}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nReminder emails sent: {sent_count}, Failed: {failed_count}'
            )
        )

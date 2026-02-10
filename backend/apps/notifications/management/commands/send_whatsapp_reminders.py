"""
Send WhatsApp appointment reminders (24h and 2h before).

Usage:
    python manage.py send_whatsapp_reminders

Run periodically via cron (e.g. every 15 minutes) or Celery Beat.
"""
from django.core.management.base import BaseCommand
from apps.notifications.tasks import run_whatsapp_reminders_24h, run_whatsapp_reminders_2h


class Command(BaseCommand):
    help = 'Send WhatsApp reminders for appointments (24h and 2h before)'

    def handle(self, *args, **options):
        s24 = run_whatsapp_reminders_24h()
        s2 = run_whatsapp_reminders_2h()
        self.stdout.write(
            self.style.SUCCESS(
                f'WhatsApp reminders sent: 24h={s24}, 2h={s2}'
            )
        )

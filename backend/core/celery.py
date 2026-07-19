import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('emr_core')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

from celery.schedules import crontab

app.conf.beat_schedule = {
    'prune-old-audit-logs-weekly': {
        'task': 'apps.organizations.tasks.prune_audit_logs',
        'schedule': crontab(day_of_week=0, hour=2, minute=0),
    },
    'appointment-reminders-hourly': {
        'task': 'apps.notifications.tasks.send_appointment_reminder_batch',
        'schedule': crontab(minute=0),
    },
    'whatsapp-reminders-15min': {
        'task': 'apps.notifications.tasks.send_whatsapp_reminder_batch',
        'schedule': crontab(minute='*/15'),
    },
    'anc-whatsapp-reminders-daily': {
        'task': 'apps.notifications.tasks.send_anc_whatsapp_reminders',
        'schedule': crontab(hour=8, minute=0),
    },
    'scheduled-backup-nightly': {
        'task': 'apps.backup.tasks.scheduled_backup',
        'schedule': crontab(hour=3, minute=0),
    },
}

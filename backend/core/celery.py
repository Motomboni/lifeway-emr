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
    'check-subscription-limits-daily': {
        'task': 'apps.organizations.tasks.check_subscription_limits',
        'schedule': crontab(hour=0, minute=0),
    },
    'prune-old-audit-logs-weekly': {
        'task': 'apps.organizations.tasks.prune_audit_logs',
        'schedule': crontab(day_of_week=0, hour=2, minute=0),
    },
    'subscription-renewal-reminders-daily': {
        'task': 'apps.organizations.tasks.send_subscription_renewal_reminders',
        'schedule': crontab(hour=8, minute=0),
    },
    'appointment-reminders-hourly': {
        'task': 'apps.notifications.tasks.send_appointment_reminder_batch',
        'schedule': crontab(minute=0),
    },
}

"""
App configuration for visits app.
"""
from django.apps import AppConfig


class VisitsConfig(AppConfig):
    """Configuration for visits app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.visits'
    verbose_name = 'Visits'

    def ready(self):
        """Import signals when app is ready."""
        import apps.visits.timeline_signals  # noqa


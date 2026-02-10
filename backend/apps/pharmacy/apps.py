"""
App configuration for pharmacy app.
"""
from django.apps import AppConfig


class PharmacyConfig(AppConfig):
    """Configuration for pharmacy app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.pharmacy'
    verbose_name = 'Pharmacy'

    def ready(self):
        """Import signals when app is ready."""
        import apps.pharmacy.signals  # noqa

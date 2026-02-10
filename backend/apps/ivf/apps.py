from django.apps import AppConfig


class IvfConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ivf'
    verbose_name = 'IVF Treatment Module'

    def ready(self):
        # Import signals when app is ready
        try:
            import apps.ivf.signals  # noqa
        except ImportError:
            pass

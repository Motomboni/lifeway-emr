from django.apps import AppConfig


class BillingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.billing'
    
    def ready(self):
        """Import signals when app is ready."""
        import apps.billing.signals  # noqa
        import apps.billing.billing_line_item_signals  # noqa


from django.apps import AppConfig


class WalletConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.wallet'
    
    def ready(self):
        """Import signals when app is ready."""
        import apps.wallet.signals  # noqa

from django.db.backends.signals import connection_created

from .celery import app as celery_app


def _configure_sqlite_pragmas(sender, connection, **kwargs):
    """WAL + busy_timeout so parallel E2E tests do not deadlock on SQLite."""
    if connection.vendor == "sqlite":
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA busy_timeout=60000;")


connection_created.connect(_configure_sqlite_pragmas)

__all__ = ("celery_app",)

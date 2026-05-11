from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from .settings import MigrationSettings


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def setup_django(settings: MigrationSettings) -> None:
    if str(settings.backend_dir) not in sys.path:
        sys.path.insert(0, str(settings.backend_dir))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings.django_settings_module)
    import django  # pylint: disable=import-outside-toplevel

    django.setup()

    # Large CSV loads on SQLite often hit "database is locked" without a busy timeout / WAL.
    from django.conf import settings as dj_settings  # pylint: disable=import-outside-toplevel
    from django.db import connections  # pylint: disable=import-outside-toplevel

    engine = dj_settings.DATABASES["default"].get("ENGINE", "")
    if "sqlite" in engine:
        timeout_ms = int(os.environ.get("MIGRATE_LMC_SQLITE_BUSY_TIMEOUT_MS", "300000"))
        with connections["default"].cursor() as cursor:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute(f"PRAGMA busy_timeout={timeout_ms}")


def ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


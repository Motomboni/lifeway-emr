"""
Celery tasks for automated database backups.
"""

import logging
import os
import shutil
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def copy_backup_offsite(local_path: str) -> str | None:
    """
    Copy a completed backup file to BACKUP_STORAGE_DIR (mounted volume, NFS, etc.).
    Returns destination path or None if not configured.
    """
    dest_root = getattr(settings, "BACKUP_STORAGE_DIR", "") or ""
    if not dest_root:
        return None

    os.makedirs(dest_root, exist_ok=True)
    filename = os.path.basename(local_path)
    dest_path = os.path.join(dest_root, filename)
    shutil.copy2(local_path, dest_path)
    logger.info("Backup copied off-site to %s", dest_path)
    return dest_path


def prune_expired_backups():
    """Delete backup files and records past retention."""
    from apps.backup.models import Backup

    retention_days = getattr(settings, "BACKUP_RETENTION_DAYS", 30)
    cutoff = timezone.now() - timedelta(days=retention_days)
    expired = Backup.objects.filter(created_at__lt=cutoff, status="COMPLETED")

    removed = 0
    for backup in expired:
        if backup.file_path and os.path.exists(backup.file_path):
            try:
                os.remove(backup.file_path)
            except OSError as e:
                logger.warning("Could not remove backup file %s: %s", backup.file_path, e)
        offsite_root = getattr(settings, "BACKUP_STORAGE_DIR", "") or ""
        if offsite_root and backup.file_path:
            offsite = os.path.join(offsite_root, os.path.basename(backup.file_path))
            if os.path.exists(offsite):
                try:
                    os.remove(offsite)
                except OSError:
                    pass
        backup.delete()
        removed += 1

    if removed:
        logger.info("Pruned %s expired backup(s).", removed)


@shared_task
def scheduled_backup():
    """Nightly full backup initiated by the system superuser."""
    if not getattr(settings, "SCHEDULED_BACKUP_ENABLED", True):
        logger.info("Scheduled backup skipped (SCHEDULED_BACKUP_ENABLED=false)")
        return

    from django.contrib.auth import get_user_model

    from apps.backup.models import Backup
    from apps.backup.utils import create_backup_file

    User = get_user_model()
    actor = User.objects.filter(is_superuser=True, is_active=True).order_by("id").first()
    if not actor:
        logger.error("Scheduled backup aborted: no active superuser")
        return

    backup = Backup.objects.create(
        backup_type="FULL",
        status="PENDING",
        description="Automated nightly backup",
        created_by=actor,
        includes_patients=True,
        includes_visits=True,
        includes_consultations=True,
        includes_lab_data=True,
        includes_radiology_data=True,
        includes_prescriptions=True,
        includes_audit_logs=True,
        expires_at=timezone.now()
        + timedelta(days=getattr(settings, "BACKUP_RETENTION_DAYS", 30)),
    )

    try:
        backup.status = "IN_PROGRESS"
        backup.started_at = timezone.now()
        backup.save(update_fields=["status", "started_at"])

        create_backup_file(backup)

        if backup.file_path:
            copy_backup_offsite(backup.file_path)

        backup.status = "COMPLETED"
        backup.completed_at = timezone.now()
        backup.save(update_fields=["status", "completed_at"])
        logger.info("Scheduled backup %s completed (%s bytes)", backup.id, backup.file_size)
    except Exception as e:
        backup.status = "FAILED"
        backup.completed_at = timezone.now()
        backup.error_message = str(e)
        backup.save(update_fields=["status", "completed_at", "error_message"])
        logger.exception("Scheduled backup %s failed", backup.id)
        raise
    finally:
        prune_expired_backups()

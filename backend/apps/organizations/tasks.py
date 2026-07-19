import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def prune_audit_logs():
    """Remove audit logs older than the configured retention period."""
    from core.audit import AuditLog

    retention_days = settings.EMR_SETTINGS.get("AUDIT_LOG_RETENTION_DAYS", 2555)
    threshold_date = timezone.now() - timedelta(days=retention_days)

    logger.info(
        "Running audit log prune (retention=%s days, before=%s)",
        retention_days,
        threshold_date.date(),
    )

    deleted_count, _ = AuditLog.objects.filter(timestamp__lt=threshold_date).delete()
    if deleted_count > 0:
        logger.info("Pruned %s audit logs.", deleted_count)

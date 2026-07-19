"""
Superuser hard-delete bypass for test-data cleanup.

Normal staff/clinical records are immutable for compliance. Django superusers
(platform operators) may permanently delete records when purging mock/tutorial data.
"""
import logging
import threading

from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)

_local = threading.local()


def is_superuser_purge_active() -> bool:
    return bool(getattr(_local, "active", False))


def can_superuser_hard_delete(user) -> bool:
    return bool(user and user.is_authenticated and getattr(user, "is_superuser", False))


class superuser_purge_context:
    """Thread-local flag so model delete() and pre_delete signals allow hard delete."""

    def __init__(self, user=None):
        self.user = user

    def __enter__(self):
        _local.active = True
        _local.user_id = getattr(self.user, "id", None)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _local.active = False
        _local.user_id = None
        return False


def log_superuser_delete(user, instance, resource_type: str) -> None:
    try:
        from core.audit import AuditLog

        visit_id = getattr(instance, "visit_id", None)
        if visit_id is None:
            visit = getattr(instance, "visit", None)
            visit_id = getattr(visit, "id", None) if visit else None

        AuditLog.log(
            user=user,
            role=getattr(user, "role", None),
            action="SUPERUSER_RECORD_DELETE",
            visit_id=visit_id,
            resource_type=resource_type,
            resource_id=getattr(instance, "pk", None),
            request=None,
            metadata={
                "model": type(instance).__name__,
                "pk": getattr(instance, "pk", None),
            },
        )
    except Exception as exc:
        logger.warning("Failed to audit superuser delete: %s", exc)


def try_superuser_destroy(viewset, request, *args, **kwargs):
    """
    If request.user is superuser, hard-delete the object and return 204.
    Otherwise return None so the viewset can apply normal compliance rules.
    """
    if not can_superuser_hard_delete(request.user):
        return None

    instance = viewset.get_object()
    resource_type = viewset.__class__.__name__.replace("ViewSet", "").lower()

    with superuser_purge_context(user=request.user):
        log_superuser_delete(request.user, instance, resource_type)
        viewset.perform_destroy(instance)

    return Response(status=status.HTTP_204_NO_CONTENT)

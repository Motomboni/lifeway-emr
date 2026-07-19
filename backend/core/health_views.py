"""
Health Check Views

Provides endpoints for monitoring application health and status.
"""

import os

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.permissions import IsPlatformAdmin


def _require_admin_for_private_health(request):
    """Return an error response when detailed health requires admin auth."""
    if settings.HEALTH_DETAILED_PUBLIC:
        return None
    if IsPlatformAdmin().has_permission(request, None):
        return None
    return Response(
        {"detail": "Authentication required."},
        status=status.HTTP_401_UNAUTHORIZED,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """
    Basic health check endpoint.

    Returns 200 if the application is running.
    """
    return Response(
        {
            "status": "healthy",
            "timestamp": timezone.now().isoformat(),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def health_detailed(request):
    """
    Detailed health check endpoint.

    Checks database and cache connectivity. Public only when
    HEALTH_DETAILED_PUBLIC=true; otherwise requires administrator auth.
    """
    auth_error = _require_admin_for_private_health(request)
    if auth_error is not None:
        return auth_error

    checks = {
        "database": False,
        "cache": False,
        "application": True,
    }

    errors = []

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = True
    except Exception as exc:
        if settings.DEBUG:
            errors.append(f"Database check failed: {exc}")

    try:
        cache.set("health_check", "ok", 10)
        if cache.get("health_check") == "ok":
            checks["cache"] = True
        elif settings.DEBUG:
            errors.append("Cache check failed: Unable to read/write")
    except Exception as exc:
        if settings.DEBUG:
            errors.append(f"Cache check failed: {exc}")

    all_healthy = all(checks.values())
    status_code = (
        status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    response_data = {
        "status": "healthy" if all_healthy else "unhealthy",
        "timestamp": timezone.now().isoformat(),
        "checks": checks,
    }

    if errors:
        response_data["errors"] = errors

    return Response(response_data, status=status_code)


@api_view(["GET"])
@permission_classes([AllowAny])
def health_info(request):
    """
    Application information endpoint.

    Returns version and environment. Detailed fields require administrator
    auth in production unless HEALTH_DETAILED_PUBLIC=true.
    """
    auth_error = _require_admin_for_private_health(request)
    if auth_error is not None:
        return auth_error

    info = {
        "application": "Modern EMR System",
        "version": getattr(settings, "APP_VERSION", os.environ.get("APP_VERSION", "2.0.0")),
        "environment": "development" if settings.DEBUG else "production",
        "timestamp": timezone.now().isoformat(),
    }

    if settings.DEBUG:
        info["database"] = settings.DATABASES["default"]["ENGINE"].split(".")[-1]
        info["debug"] = settings.DEBUG
        info["allowed_hosts"] = settings.ALLOWED_HOSTS
        info["cors_origins"] = getattr(settings, "CORS_ALLOWED_ORIGINS", [])

    return Response(info, status=status.HTTP_200_OK)

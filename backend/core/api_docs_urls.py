"""
API Documentation URLs - Swagger/OpenAPI schema and UI.

In production, routes are only mounted when API_DOCS_ENABLED=true in settings.
When mounted outside DEBUG, administrator authentication is required.
"""

from django.conf import settings
from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.permissions import AllowAny

from core.permissions import IsPlatformAdmin


def _docs_permission_classes():
    if settings.DEBUG:
        return [AllowAny]
    return [IsPlatformAdmin]


class SecuredSpectacularAPIView(SpectacularAPIView):
    def get_permissions(self):
        return [permission() for permission in _docs_permission_classes()]


class SecuredSpectacularSwaggerView(SpectacularSwaggerView):
    def get_permissions(self):
        return [permission() for permission in _docs_permission_classes()]


class SecuredSpectacularRedocView(SpectacularRedocView):
    def get_permissions(self):
        return [permission() for permission in _docs_permission_classes()]


urlpatterns = [
    path("api/schema/", SecuredSpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SecuredSpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SecuredSpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

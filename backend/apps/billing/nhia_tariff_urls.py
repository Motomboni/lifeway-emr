"""
URL configuration for NHIA tariff API.

Endpoint: /api/v1/billing/nhia-tariffs/
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .nhia_tariff_views import NHIATariffViewSet

router = DefaultRouter()
router.register(r"", NHIATariffViewSet, basename="nhia-tariff")

urlpatterns = [
    path("nhia-tariffs/", include(router.urls)),
]

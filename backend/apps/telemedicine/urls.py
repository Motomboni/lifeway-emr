"""
URL configuration for Telemedicine API.

Endpoint: /api/v1/telemedicine/
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TelemedicineSessionViewSet

router = DefaultRouter()
router.register(r"", TelemedicineSessionViewSet, basename="telemedicine")

urlpatterns = [
    path("", include(router.urls)),
]

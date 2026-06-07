"""
URL configuration for Patient API.

Endpoint: /api/v1/patients/
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .bulk_views import PatientBulkViewSet
from .views import PatientViewSet

# Create router for patient viewset
router = DefaultRouter()
router.register(r"", PatientViewSet, basename="patient")
router.register(r"bulk", PatientBulkViewSet, basename="patient-bulk")

urlpatterns = [
    path("", include(router.urls)),
]

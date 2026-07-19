"""
URL configuration for Patient API.

Endpoint: /api/v1/patients/
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .allergy_views import PatientAllergyViewSet
from .bulk_views import PatientBulkViewSet
from .views import PatientViewSet

# Create router for patient viewset
router = DefaultRouter()
router.register(r"", PatientViewSet, basename="patient")
router.register(r"bulk", PatientBulkViewSet, basename="patient-bulk")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "<int:patient_id>/allergies/",
        PatientAllergyViewSet.as_view({"get": "list", "post": "create"}),
        name="patient-allergies-list",
    ),
    path(
        "<int:patient_id>/allergies/<int:pk>/",
        PatientAllergyViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="patient-allergies-detail",
    ),
]

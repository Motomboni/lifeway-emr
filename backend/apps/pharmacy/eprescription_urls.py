"""E-Prescription URLs. Doctor only."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .eprescription_views import EPrescriptionViewSet, MedicationViewSet

router = DefaultRouter()
router.register(r"medications", MedicationViewSet, basename="eprescription-medication")
router.register(r"prescriptions", EPrescriptionViewSet, basename="eprescription")

urlpatterns = [
    path("", include(router.urls)),
]

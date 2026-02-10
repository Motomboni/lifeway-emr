"""E-Prescription URLs. Doctor only."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .eprescription_views import MedicationViewSet, EPrescriptionViewSet

router = DefaultRouter()
router.register(r'medications', MedicationViewSet, basename='eprescription-medication')
router.register(r'prescriptions', EPrescriptionViewSet, basename='eprescription')

urlpatterns = [
    path('', include(router.urls)),
]

"""
URL configuration for Admission, Ward, and Bed management.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .admission_views import (
    WardViewSet,
    BedViewSet,
    AdmissionViewSet,
    InpatientListViewSet,
)

# Main router for wards, beds, and inpatients list (not visit-scoped)
router = DefaultRouter()
router.register(r'wards', WardViewSet, basename='ward')
router.register(r'beds', BedViewSet, basename='bed')
router.register(r'inpatients', InpatientListViewSet, basename='inpatient')

# Main URL patterns (for /api/v1/admissions/)
urlpatterns = router.urls


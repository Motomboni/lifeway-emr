"""
URL configuration for Admission, Ward, and Bed management.
"""

from rest_framework.routers import DefaultRouter

from .admission_views import (
    BedViewSet,
    InpatientListViewSet,
    WardViewSet,
)

# Main router for wards, beds, and inpatients list (not visit-scoped)
router = DefaultRouter()
router.register(r"wards", WardViewSet, basename="ward")
router.register(r"beds", BedViewSet, basename="bed")
router.register(r"inpatients", InpatientListViewSet, basename="inpatient")

# Main URL patterns (for /api/v1/admissions/)
urlpatterns = router.urls

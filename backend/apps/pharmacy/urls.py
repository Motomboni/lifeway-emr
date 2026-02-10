"""
URL configuration for Prescription API - visit-scoped endpoint.

Endpoint patterns:
- /api/v1/visits/{visit_id}/prescriptions/ - Prescription CRUD
- /api/v1/visits/{visit_id}/pharmacy/dispense/ - Dedicated dispensing endpoint

This ensures prescriptions are ALWAYS visit-scoped and consultation-dependent.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PrescriptionViewSet
from .dispense_views import DispenseViewSet

# Create router for prescription viewset
router = DefaultRouter()
router.register(
    r'',
    PrescriptionViewSet,
    basename='prescription'
)

urlpatterns = [
    path('', include(router.urls)),
]

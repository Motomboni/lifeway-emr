"""
URL configuration for Patient API.

Endpoint: /api/v1/patients/
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PatientViewSet
from .bulk_views import PatientBulkViewSet

# Create router for patient viewset
router = DefaultRouter()
router.register(
    r'',
    PatientViewSet,
    basename='patient'
)
router.register(
    r'bulk',
    PatientBulkViewSet,
    basename='patient-bulk'
)

urlpatterns = [
    path('', include(router.urls)),
]

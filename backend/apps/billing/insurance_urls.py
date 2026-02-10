"""
URL configuration for Insurance API - visit-scoped endpoint.

Endpoint pattern: /api/v1/visits/{visit_id}/insurance/

This ensures insurance is ALWAYS visit-scoped.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .insurance_views import VisitInsuranceViewSet

# Create router for visit insurance viewset
router = DefaultRouter()
router.register(
    r'',
    VisitInsuranceViewSet,
    basename='visit-insurance'
)

urlpatterns = [
    path('', include(router.urls)),
]

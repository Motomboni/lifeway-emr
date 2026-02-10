"""
URL configuration for HMO Provider API.

Endpoint pattern: /api/v1/billing/hmo-providers/

Receptionist-only access.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .insurance_views import HMOProviderViewSet

router = DefaultRouter()
router.register(
    r'',
    HMOProviderViewSet,
    basename='hmo-provider'
)

urlpatterns = [
    path('', include(router.urls)),
]

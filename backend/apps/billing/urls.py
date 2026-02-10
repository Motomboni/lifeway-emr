"""
URL configuration for Payment API - visit-scoped endpoint.

Endpoint pattern: /api/v1/visits/{visit_id}/payments/

This ensures payments are ALWAYS visit-scoped.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet

# Create router for payment viewset
router = DefaultRouter()
router.register(
    r'',
    PaymentViewSet,
    basename='payment'
)

urlpatterns = [
    path('', include(router.urls)),
]

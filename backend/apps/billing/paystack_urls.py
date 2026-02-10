"""
URL configuration for Paystack PaymentIntent API - visit-scoped endpoint.

Endpoint pattern: /api/v1/visits/{visit_id}/payment-intents/

This ensures PaymentIntents are ALWAYS visit-scoped.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .paystack_views import PaymentIntentViewSet

# Create router for payment intent viewset
router = DefaultRouter()
router.register(
    r'',
    PaymentIntentViewSet,
    basename='payment-intent'
)

urlpatterns = [
    path('', include(router.urls)),
]


"""
URL configuration for Insurance Provider API.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .insurance_provider_views import InsuranceProviderViewSet

router = DefaultRouter()
router.register(r'', InsuranceProviderViewSet, basename='insurance-provider')

urlpatterns = router.urls


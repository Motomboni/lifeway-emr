"""
URL configuration for Service Catalog API.

Endpoint pattern: /api/v1/billing/service-catalog/
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .service_catalog_views import ServiceCatalogViewSet

# Create router for service catalog viewset
router = DefaultRouter()
router.register(
    r'',  # Empty prefix since 'service-catalog' is in the include path
    ServiceCatalogViewSet,
    basename='service-catalog'
)

urlpatterns = [
    path('service-catalog/', include(router.urls)),
]


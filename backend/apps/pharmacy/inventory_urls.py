"""
URL configuration for Inventory API.

Endpoint: /api/v1/inventory/
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .inventory_views import DrugInventoryViewSet, StockMovementViewSet

router = DefaultRouter()
router.register(
    r'',
    DrugInventoryViewSet,
    basename='inventory'
)
router.register(
    r'movements',
    StockMovementViewSet,
    basename='stock-movement'
)

urlpatterns = [
    path('', include(router.urls)),
]

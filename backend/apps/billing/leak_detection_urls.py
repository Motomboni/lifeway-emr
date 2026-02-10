"""
URL configuration for Revenue Leak Detection API.

Admin-only endpoints for leak detection and management.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .leak_detection_views import LeakRecordViewSet

# Create router for leak detection
router = DefaultRouter()
router.register(
    r'leaks',
    LeakRecordViewSet,
    basename='leak-record'
)

urlpatterns = [
    path('', include(router.urls)),
]


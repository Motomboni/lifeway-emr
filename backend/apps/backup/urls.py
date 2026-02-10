"""
URL configuration for Backup API.

Endpoint: /api/v1/backups/
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BackupViewSet, RestoreViewSet

router = DefaultRouter()
router.register(
    r'',
    BackupViewSet,
    basename='backup'
)
router.register(
    r'restores',
    RestoreViewSet,
    basename='restore'
)

urlpatterns = [
    path('', include(router.urls)),
]

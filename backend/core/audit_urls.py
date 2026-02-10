"""
URL configuration for Audit Log API.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .audit_views import AuditLogViewSet

router = DefaultRouter()
router.register(
    r'',
    AuditLogViewSet,
    basename='audit-log'
)

urlpatterns = [
    path('', include(router.urls)),
]

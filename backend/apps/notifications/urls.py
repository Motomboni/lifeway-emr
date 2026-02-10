"""
URL configuration for Notifications API.

Endpoint: /api/v1/notifications/
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmailNotificationViewSet

router = DefaultRouter()
router.register(
    r'',
    EmailNotificationViewSet,
    basename='notification'
)

urlpatterns = [
    path('', include(router.urls)),
]

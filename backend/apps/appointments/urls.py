"""
URL configuration for Appointment API.

Endpoint: /api/v1/appointments/
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AppointmentViewSet

router = DefaultRouter()
router.register(
    r'',
    AppointmentViewSet,
    basename='appointment'
)

urlpatterns = [
    path('', include(router.urls)),
]

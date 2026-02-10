"""
Health Check URLs
"""
from django.urls import path
from .health_views import health_check, health_detailed, health_info

urlpatterns = [
    path('api/v1/health/', health_check, name='health-check'),
    path('api/v1/health/detailed/', health_detailed, name='health-detailed'),
    path('api/v1/health/info/', health_info, name='health-info'),
]

"""
URL configuration for Pharmacy Dispensing API - visit-scoped endpoint.

Endpoint pattern: /api/v1/visits/{visit_id}/pharmacy/dispense/

This ensures dispensing is ALWAYS visit-scoped and prescription-dependent.
"""
from django.urls import path
from .dispense_views import DispenseViewSet

urlpatterns = [
    path(
        'dispense/',
        DispenseViewSet.as_view({'post': 'create'}),
        name='pharmacy-dispense'
    ),
]

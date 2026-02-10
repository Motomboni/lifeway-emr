"""
Mobile API URLs

Namespace: /api/mobile/

Lightweight endpoints for mobile patient portal.
"""
from django.urls import path
from . import mobile_api

urlpatterns = [
    path('profile/', mobile_api.mobile_profile, name='mobile-profile'),
    path('appointments/', mobile_api.mobile_appointments, name='mobile-appointments'),
    path('prescriptions/', mobile_api.mobile_prescriptions, name='mobile-prescriptions'),
    path('lab-results/', mobile_api.mobile_lab_results, name='mobile-lab-results'),
    path('bills/', mobile_api.mobile_bills, name='mobile-bills'),
    path('dashboard/', mobile_api.mobile_dashboard, name='mobile-dashboard'),
    path('sync/', mobile_api.mobile_sync, name='mobile-sync'),
]

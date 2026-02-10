"""
URL configuration for Reports API.
"""
from django.urls import path
from .views import ReportViewSet

urlpatterns = [
    # Custom action endpoints
    path('visits-summary/', ReportViewSet.as_view({'get': 'visits_summary'}), name='reports-visits-summary'),
    path('payments-summary/', ReportViewSet.as_view({'get': 'payments_summary'}), name='reports-payments-summary'),
    path('consultations-summary/', ReportViewSet.as_view({'get': 'consultations_summary'}), name='reports-consultations-summary'),
    path('dashboard-stats/', ReportViewSet.as_view({'get': 'dashboard_stats'}), name='reports-dashboard-stats'),
    path('patient-statistics/', ReportViewSet.as_view({'get': 'patient_statistics'}), name='reports-patient-statistics'),
    path('clinical-statistics/', ReportViewSet.as_view({'get': 'clinical_statistics'}), name='reports-clinical-statistics'),
    # New endpoints for enhanced reports
    path('summary/', ReportViewSet.as_view({'get': 'summary'}), name='reports-summary'),
    path('revenue-by-method/', ReportViewSet.as_view({'get': 'revenue_by_method'}), name='reports-revenue-by-method'),
    path('revenue-trend/', ReportViewSet.as_view({'get': 'revenue_trend'}), name='reports-revenue-trend'),
    path('visits-by-status/', ReportViewSet.as_view({'get': 'visits_by_status'}), name='reports-visits-by-status'),
]

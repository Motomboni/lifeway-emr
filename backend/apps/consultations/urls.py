"""
URL configuration for Consultation API - visit-scoped endpoint.

Endpoint pattern: /api/v1/visits/{visit_id}/consultation/

This ensures consultation is ALWAYS visit-scoped and cannot exist standalone.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConsultationViewSet
from .diagnosis_views import DiagnosisCodeViewSet

# Create router for consultation viewset
router = DefaultRouter()
router.register(
    r'',
    ConsultationViewSet,
    basename='consultation'
)

# Get router URLs
router_urls = router.urls

# Manually define URLs to allow PATCH on list endpoint
# Since consultation is OneToOneField, updates happen on list endpoint
from rest_framework import viewsets

urlpatterns = [
    # List endpoint with PATCH support
    path('', ConsultationViewSet.as_view({
        'get': 'list',
        'post': 'create',
        'patch': 'update_consultation',  # Custom action for PATCH
    }), name='consultation-list'),
    # Detail endpoint (for retrieve, update, delete if needed)
    path('<int:pk>/', ConsultationViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy',
    }), name='consultation-detail'),
    # Patient consultations endpoint (previous consultations for same patient)
    path('patient-consultations/', ConsultationViewSet.as_view({
        'get': 'patient_consultations',
    }), name='consultation-patient-consultations'),
    # Diagnosis codes endpoints
    path('diagnosis-codes/', DiagnosisCodeViewSet.as_view({
        'get': 'list',
        'post': 'create',
    }), name='diagnosis-code-list'),
    path('diagnosis-codes/<int:pk>/', DiagnosisCodeViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy',
    }), name='diagnosis-code-detail'),
    path('diagnosis-codes/from-ai-suggestion/', DiagnosisCodeViewSet.as_view({
        'post': 'from_ai_suggestion',
    }), name='diagnosis-code-from-ai'),
]

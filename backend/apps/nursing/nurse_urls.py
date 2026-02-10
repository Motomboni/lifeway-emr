"""
Nurse-specific URL patterns with exact paths as required.

Endpoints:
- POST /api/v1/visits/{visit_id}/vitals/
- GET /api/v1/visits/{visit_id}/vitals/
- POST /api/v1/visits/{visit_id}/nursing-notes/
- GET /api/v1/visits/{visit_id}/nursing-notes/
- POST /api/v1/visits/{visit_id}/medication-administration/
- GET /api/v1/visits/{visit_id}/medication-administration/
- POST /api/v1/visits/{visit_id}/lab-samples/
- GET /api/v1/visits/{visit_id}/lab-samples/
"""
from django.urls import path
from rest_framework.routers import DefaultRouter
from .nurse_endpoints import (
    NurseVitalSignsEndpoint,
    NurseNursingNotesEndpoint,
    NurseMedicationAdministrationEndpoint,
    NurseLabSamplesEndpoint,
)

# Create ViewSet instances for direct path mapping
vitals_viewset = NurseVitalSignsEndpoint.as_view({'get': 'list', 'post': 'create'})
nursing_notes_viewset = NurseNursingNotesEndpoint.as_view({'get': 'list', 'post': 'create'})
medication_viewset = NurseMedicationAdministrationEndpoint.as_view({'get': 'list', 'post': 'create'})
lab_samples_viewset = NurseLabSamplesEndpoint.as_view({'get': 'list', 'post': 'create'})

urlpatterns = [
    path('', vitals_viewset, name='nurse-vitals'),
    path('', nursing_notes_viewset, name='nurse-nursing-notes'),
    path('', medication_viewset, name='nurse-medication-administration'),
    path('', lab_samples_viewset, name='nurse-lab-samples'),
]

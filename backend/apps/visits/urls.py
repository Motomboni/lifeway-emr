"""
URL configuration for Visit API.

Endpoint patterns:
- /api/v1/visits/ - Visit CRUD
- /api/v1/visits/{id}/close/ - Close visit (Doctor only)

Visit-scoped endpoints:
- /api/v1/visits/{visit_id}/consultation/ - Consultation
- /api/v1/visits/{visit_id}/laboratory/ - Lab orders
- /api/v1/visits/{visit_id}/radiology/ - Radiology requests
- /api/v1/visits/{visit_id}/prescriptions/ - Prescriptions
- /api/v1/visits/{visit_id}/pharmacy/dispense/ - Dispensing
- /api/v1/visits/{visit_id}/vitals/ - Nurse vital signs (PROMPT 4)
- /api/v1/visits/{visit_id}/nursing-notes/ - Nurse nursing notes (PROMPT 4)
- /api/v1/visits/{visit_id}/medication-administration/ - Nurse medication admin (PROMPT 4)
- /api/v1/visits/{visit_id}/lab-samples/ - Nurse lab samples (PROMPT 4)
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VisitViewSet
from apps.nursing.nurse_endpoints import (
    NurseVitalSignsEndpoint,
    NurseNursingNotesEndpoint,
    NurseMedicationAdministrationEndpoint,
    NurseLabSamplesEndpoint,
)
from apps.discharges.admission_views import AdmissionViewSet
from .timeline_views import TimelineEventViewSet

# Create router for visit viewset
router = DefaultRouter()
router.register(
    r'',
    VisitViewSet,
    basename='visit'
)

# Visit-scoped endpoints (all clinical actions)
# NOTE: Patterns must be specific to avoid matching /api/v1/visits/{id}/
# The router handles the base retrieve endpoint, these handle sub-paths
visit_scoped_urls = [
    # Consultation endpoint - visit-scoped
    # Must be /consultation/ to avoid conflict with router's retrieve
    path(
        '<int:visit_id>/consultation/',
        include('apps.consultations.urls'),
        name='visit-consultation'
    ),
    # Laboratory endpoint - visit-scoped
    path(
        '<int:visit_id>/laboratory/',
        include('apps.laboratory.urls'),
        name='visit-laboratory'
    ),
    # Radiology endpoint - visit-scoped
    path(
        '<int:visit_id>/radiology/',
        include('apps.radiology.urls'),
        name='visit-radiology'
    ),
    # Prescription endpoint - visit-scoped
    path(
        '<int:visit_id>/prescriptions/',
        include('apps.pharmacy.urls'),
        name='visit-prescriptions'
    ),
    # Pharmacy dispensing endpoint - visit-scoped
    path(
        '<int:visit_id>/pharmacy/',
        include('apps.pharmacy.dispense_urls'),
        name='visit-pharmacy'
    ),
    # Payment endpoint - visit-scoped
    path(
        '<int:visit_id>/payments/',
        include('apps.billing.urls'),
        name='visit-payments'
    ),
    # Insurance endpoint - visit-scoped
    path(
        '<int:visit_id>/insurance/',
        include('apps.billing.insurance_urls'),
        name='visit-insurance'
    ),
    # Payment Intent endpoint (Paystack) - visit-scoped
    path(
        '<int:visit_id>/payment-intents/',
        include('apps.billing.paystack_urls'),
        name='visit-payment-intents'
    ),
    # Unified billing endpoints - visit-scoped
    path(
        '<int:visit_id>/billing/',
        include('apps.billing.billing_urls'),
        name='visit-billing'
    ),
    # Clinical endpoints - visit-scoped
    path(
        '<int:visit_id>/clinical/',
        include('apps.clinical.visit_urls'),
        name='visit-clinical'
    ),
    # Nursing endpoints - visit-scoped
    path(
        '<int:visit_id>/nursing/',
        include('apps.nursing.urls'),
        name='visit-nursing'
    ),
    # Nurse-specific endpoints with exact paths (PROMPT 4)
    # These must come AFTER other visit-scoped patterns to avoid conflicts
    path(
        '<int:visit_id>/vitals/',
        NurseVitalSignsEndpoint.as_view({'get': 'list', 'post': 'create'}),
        name='nurse-vitals'
    ),
    path(
        '<int:visit_id>/nursing-notes/',
        NurseNursingNotesEndpoint.as_view({'get': 'list', 'post': 'create'}),
        name='nurse-nursing-notes'
    ),
    path(
        '<int:visit_id>/medication-administration/',
        NurseMedicationAdministrationEndpoint.as_view({'get': 'list', 'post': 'create'}),
        name='nurse-medication-administration'
    ),
    path(
        '<int:visit_id>/lab-samples/',
        NurseLabSamplesEndpoint.as_view({'get': 'list', 'post': 'create'}),
        name='nurse-lab-samples'
    ),
    # Documents endpoint - visit-scoped
    path(
        '<int:visit_id>/documents/',
        include('apps.documents.urls'),
        name='visit-documents'
    ),
    # Referrals endpoint - visit-scoped
    path(
        '<int:visit_id>/referrals/',
        include('apps.referrals.urls'),
        name='visit-referrals'
    ),
    # Discharge Summaries endpoint - visit-scoped
    path(
        '<int:visit_id>/discharge-summaries/',
        include('apps.discharges.urls'),
        name='visit-discharges'
    ),
    # Admission endpoint - visit-scoped
    path(
        '<int:visit_id>/admissions/',
        include([
            path('', AdmissionViewSet.as_view({'get': 'list', 'post': 'create'}), name='visit-admission-list'),
            path('<int:pk>/', AdmissionViewSet.as_view({
                'get': 'retrieve',
                'put': 'update',
                'patch': 'partial_update',
            }), name='visit-admission-detail'),
            path('<int:pk>/discharge/', AdmissionViewSet.as_view({'post': 'discharge'}), name='visit-admission-discharge'),
            path('<int:pk>/transfer/', AdmissionViewSet.as_view({'post': 'transfer'}), name='visit-admission-transfer'),
        ]),
        name='visit-admissions'
    ),
    # AI Integration endpoint - visit-scoped
    path(
        '<int:visit_id>/ai/',
        include('apps.ai_integration.urls'),
        name='visit-ai'
    ),
    # Timeline endpoint - visit-scoped
    path(
        '<int:visit_id>/timeline/',
        TimelineEventViewSet.as_view({'get': 'list'}),
        name='visit-timeline'
    ),
]

# IMPORTANT: Router URLs must come BEFORE visit-scoped URLs
# This ensures that /api/v1/visits/{id}/ is handled by the router's retrieve endpoint
# before the visit-scoped patterns can match
# However, the visit-scoped pattern '<int:visit_id>/' is too broad and will still match
# So we need to make visit-scoped patterns more specific
urlpatterns = router.urls + visit_scoped_urls

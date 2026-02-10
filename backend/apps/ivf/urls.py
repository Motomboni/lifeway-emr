"""
IVF Module URL Configuration

Provides endpoints for IVF cycle management and related procedures.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    IVFCycleViewSet, OvarianStimulationViewSet, OocyteRetrievalViewSet,
    SpermAnalysisViewSet, EmbryoViewSet, EmbryoTransferViewSet,
    IVFMedicationViewSet, IVFOutcomeViewSet, IVFConsentViewSet,
    EmbryoInventoryViewSet, IVFPatientsListView, IVFVisitsListView,
)

# Main router for top-level resources
router = DefaultRouter()
router.register(r'cycles', IVFCycleViewSet, basename='ivf-cycle')
router.register(r'sperm-analyses', SpermAnalysisViewSet, basename='sperm-analysis')
router.register(r'outcomes', IVFOutcomeViewSet, basename='ivf-outcome')
router.register(r'embryo-inventory', EmbryoInventoryViewSet, basename='embryo-inventory')

# Nested URL patterns for cycle-scoped resources
# Using manual URL patterns instead of nested routers to avoid extra dependency

urlpatterns = [
    path('', include(router.urls)),
    path('patients/', IVFPatientsListView.as_view(), name='ivf-patients-list'),
    path('visits/', IVFVisitsListView.as_view(), name='ivf-visits-list'),
    # Cycle-scoped stimulation records
    path('cycles/<int:cycle_pk>/stimulation/', 
         OvarianStimulationViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='cycle-stimulation-list'),
    path('cycles/<int:cycle_pk>/stimulation/<int:pk>/', 
         OvarianStimulationViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}),
         name='cycle-stimulation-detail'),
    
    # Cycle-scoped oocyte retrieval
    path('cycles/<int:cycle_pk>/retrieval/', 
         OocyteRetrievalViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='cycle-retrieval-list'),
    path('cycles/<int:cycle_pk>/retrieval/<int:pk>/', 
         OocyteRetrievalViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}),
         name='cycle-retrieval-detail'),
    
    # Cycle-scoped embryos
    path('cycles/<int:cycle_pk>/embryos/', 
         EmbryoViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='cycle-embryo-list'),
    path('cycles/<int:cycle_pk>/embryos/<int:pk>/', 
         EmbryoViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}),
         name='cycle-embryo-detail'),
    path('cycles/<int:cycle_pk>/embryos/<int:pk>/freeze/', 
         EmbryoViewSet.as_view({'post': 'freeze'}),
         name='cycle-embryo-freeze'),
    path('cycles/<int:cycle_pk>/embryos/<int:pk>/thaw/', 
         EmbryoViewSet.as_view({'post': 'thaw'}),
         name='cycle-embryo-thaw'),
    path('cycles/<int:cycle_pk>/embryos/<int:pk>/dispose/', 
         EmbryoViewSet.as_view({'post': 'dispose'}),
         name='cycle-embryo-dispose'),
    
    # Cycle-scoped transfers
    path('cycles/<int:cycle_pk>/transfers/', 
         EmbryoTransferViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='cycle-transfer-list'),
    path('cycles/<int:cycle_pk>/transfers/<int:pk>/', 
         EmbryoTransferViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}),
         name='cycle-transfer-detail'),
    
    # Cycle-scoped medications
    path('cycles/<int:cycle_pk>/medications/', 
         IVFMedicationViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='cycle-medication-list'),
    path('cycles/<int:cycle_pk>/medications/<int:pk>/', 
         IVFMedicationViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}),
         name='cycle-medication-detail'),
    
    # Cycle-scoped consents
    path('cycles/<int:cycle_pk>/consents/', 
         IVFConsentViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='cycle-consent-list'),
    path('cycles/<int:cycle_pk>/consents/<int:pk>/', 
         IVFConsentViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}),
         name='cycle-consent-detail'),
    path('cycles/<int:cycle_pk>/consents/<int:pk>/sign/', 
         IVFConsentViewSet.as_view({'post': 'sign'}),
         name='cycle-consent-sign'),
    path('cycles/<int:cycle_pk>/consents/<int:pk>/revoke/', 
         IVFConsentViewSet.as_view({'post': 'revoke'}),
         name='cycle-consent-revoke'),
]

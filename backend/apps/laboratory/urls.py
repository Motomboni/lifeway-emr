"""
URL configuration for Lab Order API - visit-scoped endpoint.

Endpoint patterns:
- /api/v1/visits/{visit_id}/laboratory/ - Lab orders
- /api/v1/visits/{visit_id}/laboratory/results/ - Lab results

This ensures lab orders and results are ALWAYS visit-scoped and consultation-dependent.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LabOrderViewSet
from .result_views import LabResultViewSet

# Create router for lab order viewset
router = DefaultRouter()
router.register(
    r'',
    LabOrderViewSet,
    basename='lab-order'
)

# Use explicit path patterns for lab results to ensure POST works correctly
# This avoids router issues with nested endpoints
urlpatterns = router.urls + [
    # Lab results - list and create (POST)
    path(
        'results/',
        LabResultViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='lab-result-list'
    ),
    # Lab results - detail operations
    path(
        'results/<int:pk>/',
        LabResultViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy'
        }),
        name='lab-result-detail'
    ),
]

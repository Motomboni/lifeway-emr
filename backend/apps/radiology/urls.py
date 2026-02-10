"""
URL configuration for Radiology Request API - visit-scoped endpoint.

Endpoint patterns:
- /api/v1/visits/{visit_id}/radiology/ - Radiology requests
- /api/v1/visits/{visit_id}/radiology/results/ - Radiology results

Note: Offline image sync endpoints are in offline_image_urls.py

This ensures radiology requests and results are ALWAYS visit-scoped and consultation-dependent.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RadiologyRequestViewSet, RadiologyOrderViewSet
from .result_views import RadiologyResultViewSet
from .image_upload_views import ImageUploadSessionViewSet

# Router for radiology requests (from Service Catalog)
router = DefaultRouter()
router.register(
    r'',
    RadiologyRequestViewSet,  # Changed from RadiologyOrderViewSet to RadiologyRequestViewSet
    basename='radiology-request'
)

# Router for image upload sessions
upload_router = DefaultRouter()
upload_router.register(
    r'upload-sessions',
    ImageUploadSessionViewSet,
    basename='image-upload-session'
)

# Use explicit path patterns for radiology results to avoid router edge cases
urlpatterns = router.urls + [
    # Radiology results - list/create
    path(
        'results/',
        RadiologyResultViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='radiology-result-list'
    ),
    # Radiology results - detail operations
    path(
        'results/<int:pk>/',
        RadiologyResultViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy'
        }),
        name='radiology-result-detail'
    ),
    # Image upload sessions - offline-first upload system
    path('', include(upload_router.urls)),
]


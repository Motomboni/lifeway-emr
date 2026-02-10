"""
URL configuration for Offline Image Sync API and PACS-lite Viewer.

Endpoint patterns:
- /api/v1/radiology/offline-images/ - Offline image metadata management
- /api/v1/radiology/images/ - Radiology images (read-only)
- /api/v1/radiology/studies/ - Radiology studies (read-only, PACS-lite)
- /api/v1/radiology/series/ - Radiology series (read-only, PACS-lite)

Per EMR Context Document v2 (LOCKED):
- Metadata syncs before binaries
- No image is deleted locally until server ACK
- PACS-lite: Group by Study/Series, Expose viewer URLs, Enforce read-only access
"""
from rest_framework.routers import DefaultRouter
from .offline_sync_views import OfflineImageMetadataViewSet
from .viewer_views import RadiologyStudyViewSet, RadiologyImageViewSet

# Offline image sync and PACS-lite router
router = DefaultRouter()
router.register(
    r'offline-images',
    OfflineImageMetadataViewSet,
    basename='offline-image-metadata'
)
router.register(
    r'studies',
    RadiologyStudyViewSet,
    basename='radiology-study'
)
router.register(
    r'images',
    RadiologyImageViewSet,
    basename='radiology-image'
)

urlpatterns = router.urls


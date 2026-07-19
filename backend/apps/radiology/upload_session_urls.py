"""
URL configuration for Image Upload Sessions.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .image_upload_views import ImageUploadSessionViewSet

router = DefaultRouter()
router.register(r"sessions", ImageUploadSessionViewSet, basename="upload-session")

urlpatterns = [
    path("", include(router.urls)),
]

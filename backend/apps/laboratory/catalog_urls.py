"""
URL configuration for Lab Test Catalog (global endpoint).
"""

from rest_framework.routers import DefaultRouter

from .catalog_views import LabTestCatalogViewSet

router = DefaultRouter()
router.register(r"lab-tests", LabTestCatalogViewSet, basename="lab-test-catalog")

urlpatterns = router.urls

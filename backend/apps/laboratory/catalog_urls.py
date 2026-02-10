"""
URL configuration for Lab Test Catalog (global endpoint).
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .catalog_views import LabTestCatalogViewSet

router = DefaultRouter()
router.register(r'lab-tests', LabTestCatalogViewSet, basename='lab-test-catalog')

urlpatterns = router.urls

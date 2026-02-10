"""
URL configuration for Radiology Test Templates (global, not visit-scoped).
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .template_views import RadiologyTestTemplateViewSet

router = DefaultRouter()
router.register(r'templates', RadiologyTestTemplateViewSet, basename='radiology-test-template')

urlpatterns = router.urls


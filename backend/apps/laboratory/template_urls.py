"""
URL configuration for Lab Test Templates (global, not visit-scoped).
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .template_views import LabTestTemplateViewSet

router = DefaultRouter()
router.register(r'templates', LabTestTemplateViewSet, basename='lab-test-template')

urlpatterns = router.urls


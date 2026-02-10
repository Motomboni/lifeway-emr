"""
Global Clinical URLs.
Used in core/urls.py for templates
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClinicalTemplateViewSet

router = DefaultRouter()
router.register(r'templates', ClinicalTemplateViewSet, basename='clinical-templates')

urlpatterns = router.urls

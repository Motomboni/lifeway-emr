"""
URL configuration for Radiology Study Types Catalog (global endpoint).
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .study_types_views import RadiologyStudyTypeViewSet

router = DefaultRouter()
router.register(r'study-types', RadiologyStudyTypeViewSet, basename='radiology-study-type')

urlpatterns = router.urls

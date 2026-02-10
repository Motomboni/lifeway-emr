"""
URL configuration for Patient Portal endpoints.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .portal_views import PatientPortalViewSet

router = DefaultRouter()
router.register(r'', PatientPortalViewSet, basename='patient-portal')

urlpatterns = router.urls

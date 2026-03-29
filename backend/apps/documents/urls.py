"""
URL configuration for Documents API - visit-scoped.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MedicalDocumentViewSet

router = DefaultRouter()
# Prefix must be '' — parent URL already ends with /documents/ (see apps.visits.urls).
router.register(r'', MedicalDocumentViewSet, basename='medical-documents')

urlpatterns = [
    path('', include(router.urls)),
]

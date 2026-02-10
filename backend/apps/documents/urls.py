"""
URL configuration for Documents API - visit-scoped.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MedicalDocumentViewSet

router = DefaultRouter()
router.register(r'documents', MedicalDocumentViewSet, basename='medical-documents')

urlpatterns = [
    path('', include(router.urls)),
]

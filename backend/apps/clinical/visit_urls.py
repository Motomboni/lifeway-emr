"""
Visit-scoped Clinical URLs.
Used in apps/visits/urls.py
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VitalSignsViewSet, ClinicalAlertViewSet
from .operation_views import OperationNoteViewSet

router = DefaultRouter()
router.register(r'vital-signs', VitalSignsViewSet, basename='vital-signs')
router.register(r'alerts', ClinicalAlertViewSet, basename='clinical-alerts')
router.register(r'operation-notes', OperationNoteViewSet, basename='operation-notes')

urlpatterns = [
    path('', include(router.urls)),
]

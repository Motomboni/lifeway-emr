"""
Visit-scoped Clinical URLs.
Used in apps/visits/urls.py
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .operation_views import OperationNoteViewSet
from .views import ClinicalAlertViewSet, VitalSignsViewSet

router = DefaultRouter()
router.register(r"vital-signs", VitalSignsViewSet, basename="vital-signs")
router.register(r"alerts", ClinicalAlertViewSet, basename="clinical-alerts")
router.register(r"operation-notes", OperationNoteViewSet, basename="operation-notes")

urlpatterns = [
    path("", include(router.urls)),
]

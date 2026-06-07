"""
Visit-scoped Nursing URLs.
Used in apps/visits/urls.py
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    LabSampleCollectionViewSet,
    MedicationAdministrationViewSet,
    NursingNoteViewSet,
)

router = DefaultRouter()
router.register(r"nursing-notes", NursingNoteViewSet, basename="nursing-notes")
router.register(
    r"medication-administrations",
    MedicationAdministrationViewSet,
    basename="medication-administrations",
)
router.register(
    r"lab-sample-collections",
    LabSampleCollectionViewSet,
    basename="lab-sample-collections",
)

urlpatterns = [
    path("", include(router.urls)),
]

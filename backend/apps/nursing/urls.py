"""
Visit-scoped Nursing URLs.
Used in apps/visits/urls.py
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NursingNoteViewSet,
    MedicationAdministrationViewSet,
    LabSampleCollectionViewSet,
)

router = DefaultRouter()
router.register(r'nursing-notes', NursingNoteViewSet, basename='nursing-notes')
router.register(r'medication-administrations', MedicationAdministrationViewSet, basename='medication-administrations')
router.register(r'lab-sample-collections', LabSampleCollectionViewSet, basename='lab-sample-collections')

urlpatterns = [
    path('', include(router.urls)),
]


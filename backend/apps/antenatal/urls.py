"""
Antenatal Module URL Configuration
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AntenatalLabViewSet,
    AntenatalMedicationViewSet,
    AntenatalOutcomeViewSet,
    AntenatalRecordViewSet,
    AntenatalUltrasoundViewSet,
    AntenatalVisitViewSet,
)

router = DefaultRouter()
router.register(r"records", AntenatalRecordViewSet, basename="antenatal-record")
router.register(r"visits", AntenatalVisitViewSet, basename="antenatal-visit")
router.register(
    r"ultrasounds", AntenatalUltrasoundViewSet, basename="antenatal-ultrasound"
)
router.register(r"labs", AntenatalLabViewSet, basename="antenatal-lab")
router.register(
    r"medications", AntenatalMedicationViewSet, basename="antenatal-medication"
)
router.register(r"outcomes", AntenatalOutcomeViewSet, basename="antenatal-outcome")

urlpatterns = [
    path("", include(router.urls)),
]

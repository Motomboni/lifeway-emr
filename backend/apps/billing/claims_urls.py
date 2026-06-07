"""Insurance claims and policies URLs. Billing staff only."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .claims_views import ClaimViewSet, InsurancePolicyViewSet

router = DefaultRouter()
router.register(r"policies", InsurancePolicyViewSet, basename="claim-policy")
router.register(r"claims", ClaimViewSet, basename="claim")

urlpatterns = [
    path("", include(router.urls)),
]

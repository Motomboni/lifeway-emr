"""NHIA claim pack batch export URLs."""

from django.urls import path

from .claim_pack_views import BatchClaimPackView
from .nhia_compliance_views import NHIAComplianceDashboardView
from .nhia_claim_lifecycle_urls import urlpatterns as nhia_lifecycle_urls

urlpatterns = [
    path("claim-pack/", BatchClaimPackView.as_view(), name="batch-claim-pack"),
    path(
        "nhia-compliance/",
        NHIAComplianceDashboardView.as_view(),
        name="nhia-compliance-dashboard",
    ),
] + nhia_lifecycle_urls

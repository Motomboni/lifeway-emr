"""NHIA claim lifecycle URLs."""

from django.urls import path

from . import nhia_claim_lifecycle_views as views

urlpatterns = [
    path(
        "nhia-claims/",
        views.nhia_claim_lifecycle_list,
        name="nhia-claim-lifecycle-list",
    ),
    path(
        "nhia-claims/summary/",
        views.nhia_claim_lifecycle_summary,
        name="nhia-claim-lifecycle-summary",
    ),
    path(
        "visits/<int:visit_id>/nhia-claim/",
        views.nhia_claim_lifecycle_action,
        name="nhia-claim-lifecycle-action",
    ),
]

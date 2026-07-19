"""Payment reconciliation URL routes."""

from django.urls import path

from . import payment_reconciliation_views as views

urlpatterns = [
    path(
        "payment-reconciliation/",
        views.payment_reconciliation_list,
        name="payment-reconciliation-list",
    ),
    path(
        "payment-reconciliation/<int:rec_id>/match/",
        views.payment_reconciliation_match,
        name="payment-reconciliation-match",
    ),
    path(
        "payment-reconciliation/<int:rec_id>/dispute/",
        views.payment_reconciliation_dispute,
        name="payment-reconciliation-dispute",
    ),
]

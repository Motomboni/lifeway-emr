"""
URL configuration for insurance claim endpoints.
"""
from django.urls import path
from .insurance_claim_views import SubmitInsuranceClaimView, UpdateInsuranceClaimStatusView

urlpatterns = [
    path('submit-claim/', SubmitInsuranceClaimView.as_view(), name='submit-insurance-claim'),
    path('update-claim-status/', UpdateInsuranceClaimStatusView.as_view(), name='update-insurance-claim-status'),
]


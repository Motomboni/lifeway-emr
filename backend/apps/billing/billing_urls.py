"""
URL configuration for unified billing endpoints - visit-scoped.

Endpoint pattern: /api/v1/visits/{visit_id}/billing/

This ensures all billing operations are ALWAYS visit-scoped.
"""

from django.urls import path

from .billing_endpoints import (
    BillingChargesView,
    BillingInsuranceView,
    BillingPaymentsView,
    BillingSummaryView,
    BillingWalletDebitView,
)
from .claim_pack_views import VisitClaimPackView
from .nhia_charge_views import NHIAScribeChargesView
from .receipt_views import (
    BillingStatementView,
    InvoiceView,
    ReceiptView,
    SendInvoiceEmailView,
    SendReceiptEmailView,
    test_logo_view,
)

urlpatterns = [
    # GET billing summary
    path("summary/", BillingSummaryView.as_view(), name="billing-summary"),
    # POST create charge (MISC only)
    path("charges/", BillingChargesView.as_view(), name="billing-charges"),
    # POST add NHIA scribe-validated charges (Doctor/Receptionist)
    path(
        "nhia-charges/",
        NHIAScribeChargesView.as_view(),
        name="billing-nhia-charges",
    ),
    # GET NHIA/HMO claim pack export
    path("claim-pack/", VisitClaimPackView.as_view(), name="billing-claim-pack"),
    # POST create payment
    path("payments/", BillingPaymentsView.as_view(), name="billing-payments"),
    # POST create wallet debit
    path(
        "wallet-debit/", BillingWalletDebitView.as_view(), name="billing-wallet-debit"
    ),
    # POST create insurance
    path("insurance/", BillingInsuranceView.as_view(), name="billing-insurance"),
    # GET/POST generate receipt
    path("receipt/", ReceiptView.as_view(), name="billing-receipt"),
    # GET generate invoice
    path("invoice/", InvoiceView.as_view(), name="billing-invoice"),
    # GET generate billing statement
    path("statement/", BillingStatementView.as_view(), name="billing-statement"),
    # POST send receipt via email
    path(
        "receipt/send-email/",
        SendReceiptEmailView.as_view(),
        name="billing-receipt-send-email",
    ),
    # POST send invoice via email
    path(
        "invoice/send-email/",
        SendInvoiceEmailView.as_view(),
        name="billing-invoice-send-email",
    ),
    # GET test logo loading (debug endpoint)
    path("test-logo/", test_logo_view, name="billing-test-logo"),
]

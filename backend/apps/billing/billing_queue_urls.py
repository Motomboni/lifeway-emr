"""
URL configuration for central billing queue (Receptionist dashboard).
"""
from django.urls import path
from .billing_queue_views import (
    BillingPaymentHistoryView,
    BillingPendingQueueView,
    DeferredLegacyPaymentSettleView,
    DeferredLegacyPaymentsView,
)

urlpatterns = [
    path('pending-queue/', BillingPendingQueueView.as_view(), name='billing-pending-queue'),
    path('payments/', BillingPaymentHistoryView.as_view(), name='billing-payment-history'),
    path('deferred-payments/', DeferredLegacyPaymentsView.as_view(), name='billing-deferred-payments'),
    path(
        'deferred-payments/<int:charge_id>/settle/',
        DeferredLegacyPaymentSettleView.as_view(),
        name='billing-deferred-payment-settle',
    ),
]

"""
URL configuration for central billing queue (Receptionist dashboard).
"""

from django.urls import path

from .billing_queue_views import BillingPendingQueueView
from .deferred_payment_views import DeferredPaymentSettleView, DeferredPaymentsListView

urlpatterns = [
    path(
        "pending-queue/",
        BillingPendingQueueView.as_view(),
        name="billing-pending-queue",
    ),
    path(
        "deferred-payments/",
        DeferredPaymentsListView.as_view(),
        name="billing-deferred-payments",
    ),
    path(
        "deferred-payments/<int:charge_id>/settle/",
        DeferredPaymentSettleView.as_view(),
        name="billing-deferred-payment-settle",
    ),
]

"""
URL configuration for central billing queue (Receptionist dashboard).
"""
from django.urls import path
from .billing_queue_views import BillingPaymentHistoryView, BillingPendingQueueView

urlpatterns = [
    path('pending-queue/', BillingPendingQueueView.as_view(), name='billing-pending-queue'),
    path('payments/', BillingPaymentHistoryView.as_view(), name='billing-payment-history'),
]

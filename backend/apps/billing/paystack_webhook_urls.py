"""
URL configuration for Paystack webhook endpoint.

Endpoint: /api/v1/billing/paystack/webhook/

This is a public endpoint (no auth required) but signature-verified.
"""
from django.urls import path
from .paystack_views import paystack_webhook

urlpatterns = [
    path('', paystack_webhook, name='paystack-webhook'),
]


"""
Stripe webhook URL configuration.

Endpoint: /api/v1/subscriptions/stripe/webhook/
Public, signature-verified.
"""

from django.urls import path

from .stripe_views import stripe_webhook

urlpatterns = [
    path("", stripe_webhook, name="stripe-webhook"),
]

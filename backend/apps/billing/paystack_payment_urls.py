"""
URL routing for simplified Paystack payment endpoints.
"""
from django.urls import path
from .paystack_payment_views import PaystackInitiateView, paystack_webhook_view

urlpatterns = [
    path('paystack/initiate/', PaystackInitiateView.as_view(), name='paystack-initiate'),
    path('paystack/webhook/', paystack_webhook_view, name='paystack-webhook'),
]


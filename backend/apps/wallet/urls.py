"""
URLs for wallet app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WalletViewSet, PaymentChannelViewSet
from .wallet_payment_views import WalletTopUpView, WalletPayView

router = DefaultRouter()
router.register(r'wallets', WalletViewSet, basename='wallet')
router.register(r'payment-channels', PaymentChannelViewSet, basename='payment-channel')

urlpatterns = [
    # Simplified endpoints
    path('topup/', WalletTopUpView.as_view(), name='wallet-topup'),
    path('pay/', WalletPayView.as_view(), name='wallet-pay'),
    # Existing router endpoints
    path('', include(router.urls)),
]

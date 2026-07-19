"""Paystack configuration and mock gateway helpers."""

from decimal import Decimal

import pytest
from django.test import override_settings


def test_placeholder_keys_are_not_configured():
    from apps.billing.paystack_config import is_paystack_configured

    with override_settings(
        PAYSTACK_SECRET_KEY="your-paystack-secret-key",
        PAYSTACK_PUBLIC_KEY="your-paystack-public-key",
        PAYSTACK_MOCK="",
        DEBUG=True,
    ):
        assert is_paystack_configured() is False


def test_mock_enabled_in_debug_without_keys():
    from apps.billing.paystack_config import is_paystack_mock_enabled

    with override_settings(
        PAYSTACK_SECRET_KEY="",
        PAYSTACK_PUBLIC_KEY="",
        PAYSTACK_MOCK="",
        DEBUG=True,
    ):
        assert is_paystack_mock_enabled() is True


def test_mock_gateway_returns_local_callback():
    from apps.wallet.services import PaymentGatewayService

    with override_settings(
        PAYSTACK_MOCK="true",
        PAYSTACK_SECRET_KEY="",
        PAYSTACK_PUBLIC_KEY="",
        FRONTEND_URL="http://localhost:3001",
        DEBUG=True,
    ):
        gateway = PaymentGatewayService("PAYSTACK")
        result = gateway.initialize_payment(
            email="patient@example.com",
            amount=Decimal("1000.00"),
            reference="WALLET_1_TESTREF",
            callback_url="http://localhost:3001/wallet/callback",
        )
        assert result["mock"] is True
        url = result["data"]["authorization_url"]
        assert "reference=WALLET_1_TESTREF" in url
        assert "/wallet/callback" in url

        verified = gateway.verify_payment("WALLET_1_TESTREF")
        assert verified["data"]["status"] == "success"
        assert verified["data"]["gateway_response"] == "Successful"

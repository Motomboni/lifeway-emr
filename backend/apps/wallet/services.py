"""
Payment gateway services for wallet transactions.

Supports Paystack live/test keys, plus a local mock gateway for development.
"""

from decimal import Decimal
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests
from django.conf import settings

from apps.billing.paystack_config import (
    get_paystack_secret_key,
    is_paystack_configured,
    is_paystack_mock_enabled,
    require_paystack_configured,
)


class PaystackService:
    """
    Paystack payment gateway integration.

    Documentation: https://paystack.com/docs/api/
    """

    def __init__(self):
        require_paystack_configured()
        self.secret_key = get_paystack_secret_key()
        self.public_key = getattr(settings, "PAYSTACK_PUBLIC_KEY", "")
        self.base_url = "https://api.paystack.co"

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    def initialize_transaction(
        self,
        email: str,
        amount: Decimal,
        reference: str,
        metadata: Optional[Dict[str, Any]] = None,
        callback_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Initialize a Paystack transaction.

        Args:
            email: Customer email
            amount: Amount in NGN
            reference: Unique transaction reference
            metadata: Additional metadata
            callback_url: Callback URL after payment

        Returns:
            Dict with authorization_url and access_code
        """
        amount_in_kobo = int(amount * 100)

        payload = {
            "email": email,
            "amount": amount_in_kobo,
            "reference": reference,
            "metadata": metadata or {},
        }

        if callback_url:
            payload["callback_url"] = callback_url

        try:
            response = requests.post(
                f"{self.base_url}/transaction/initialize",
                json=payload,
                headers=self._get_headers(),
                timeout=30,
            )
            if response.status_code == 401:
                raise ValueError(
                    "Paystack rejected the API key (401 Unauthorized). "
                    "Replace placeholder PAYSTACK_SECRET_KEY / PAYSTACK_PUBLIC_KEY "
                    "with valid sk_test_/pk_test_ keys from https://dashboard.paystack.com."
                )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as exc:
            detail = ""
            try:
                detail = exc.response.json().get("message") or exc.response.text
            except Exception:
                detail = str(exc)
            raise ValueError(f"Paystack initialize failed: {detail}") from exc

    def verify_transaction(self, reference: str) -> Dict[str, Any]:
        """Verify a Paystack transaction."""
        try:
            response = requests.get(
                f"{self.base_url}/transaction/verify/{reference}",
                headers=self._get_headers(),
                timeout=30,
            )
            if response.status_code == 401:
                raise ValueError(
                    "Paystack rejected the API key (401 Unauthorized). "
                    "Check PAYSTACK_SECRET_KEY in backend/.env."
                )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as exc:
            detail = ""
            try:
                detail = exc.response.json().get("message") or exc.response.text
            except Exception:
                detail = str(exc)
            raise ValueError(f"Paystack verify failed: {detail}") from exc


class MockPaystackService:
    """Local development gateway that does not call Paystack."""

    def initialize_transaction(
        self,
        email: str,
        amount: Decimal,
        reference: str,
        metadata: Optional[Dict[str, Any]] = None,
        callback_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        frontend = getattr(settings, "FRONTEND_URL", "http://localhost:3001").rstrip(
            "/"
        )
        callback = callback_url or f"{frontend}/wallet/callback"
        separator = "&" if "?" in callback else "?"
        authorization_url = f"{callback}{separator}{urlencode({'reference': reference, 'mock': '1'})}"
        return {
            "status": True,
            "message": "Mock payment initialized",
            "data": {
                "authorization_url": authorization_url,
                "access_code": f"mock_{reference[-8:]}",
                "reference": reference,
            },
            "mock": True,
        }

    def verify_transaction(self, reference: str) -> Dict[str, Any]:
        return {
            "status": True,
            "message": "Verification successful",
            "data": {
                "status": "success",
                "gateway_response": "Successful",
                "reference": reference,
                "amount": 0,
            },
            "mock": True,
        }


class PaymentGatewayService:
    """
    Unified service for multiple payment gateways.
    """

    def __init__(self, channel_type: str):
        self.channel_type = channel_type

        if channel_type != "PAYSTACK":
            raise ValueError(f"Unsupported payment channel: {channel_type}")

        if is_paystack_mock_enabled():
            self.gateway = MockPaystackService()
            self._mode = "mock"
        elif is_paystack_configured():
            self.gateway = PaystackService()
            self._mode = "live"
        else:
            require_paystack_configured()

    def initialize_payment(
        self,
        email: str,
        amount: Decimal,
        reference: str,
        metadata: Optional[Dict[str, Any]] = None,
        callback_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Initialize payment with the configured gateway."""
        return self.gateway.initialize_transaction(
            email=email,
            amount=amount,
            reference=reference,
            metadata=metadata,
            callback_url=callback_url,
        )

    def verify_payment(self, reference: str) -> Dict[str, Any]:
        """Verify payment with the configured gateway."""
        return self.gateway.verify_transaction(reference)

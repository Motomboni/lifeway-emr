"""
Flutterwave integration for SaaS subscription plan upgrades (Nigeria).

Optional provider when SAAS_PAYMENT_PROVIDER=flutterwave.
"""

import logging
import uuid
from decimal import Decimal
from typing import Any, Dict, Optional

import requests
from django.conf import settings
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

SAAS_METADATA_SOURCE = "emr_saas_subscription"


class FlutterwaveSaasService:
    def __init__(self):
        self.secret_key = getattr(settings, "FLUTTERWAVE_SECRET_KEY", "") or ""
        self.base_url = "https://api.flutterwave.com/v3"

    def is_configured(self) -> bool:
        return bool(self.secret_key.strip())

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    def build_reference(self, organization_id: int) -> str:
        return f"SAAS-FW-{organization_id}-{uuid.uuid4().hex[:12].upper()}"

    def initialize_plan_payment(
        self,
        organization,
        plan,
        reference: str,
        callback_url: Optional[str] = None,
        customer_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.is_configured():
            raise ValidationError(
                "Flutterwave is not configured. Set FLUTTERWAVE_SECRET_KEY."
            )

        amount = plan.price_monthly
        if amount <= 0:
            raise ValidationError("Plan has no payable monthly price.")

        email = customer_email or organization.email or "billing@clinic.local"
        payload = {
            "tx_ref": reference,
            "amount": str(amount),
            "currency": (plan.currency or "NGN").upper(),
            "redirect_url": callback_url or "",
            "customer": {
                "email": email,
                "name": organization.name[:100],
            },
            "meta": {
                "organization_id": organization.id,
                "plan_slug": plan.slug,
                "source": SAAS_METADATA_SOURCE,
            },
        }

        response = requests.post(
            f"{self.base_url}/payments",
            json=payload,
            headers=self._headers(),
            timeout=30,
        )
        try:
            body = response.json()
        except ValueError:
            body = {}
        if not response.ok or body.get("status") != "success":
            msg = body.get("message") or "Flutterwave initialization failed"
            raise ValidationError(msg)

        return body

    def verify_transaction(self, reference: str) -> Dict[str, Any]:
        if not self.is_configured():
            raise ValidationError("Flutterwave is not configured.")

        response = requests.get(
            f"{self.base_url}/transactions/verify_by_reference?tx_ref={reference}",
            headers=self._headers(),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def is_successful(self, fw_response: Dict[str, Any]) -> bool:
        if fw_response.get("status") != "success":
            return False
        data = fw_response.get("data", {})
        return data.get("status") == "successful"

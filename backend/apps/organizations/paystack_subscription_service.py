"""
Paystack integration for SaaS subscription plan upgrades (Nigeria).

Supports one-time checkout and recurring subscriptions via Paystack Plans API.
Metadata contains only organization_id and plan_slug — no PHI.
"""

import logging
import uuid
from typing import Any, Dict, Optional

import requests
from django.conf import settings
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

SAAS_METADATA_SOURCE = "emr_saas_subscription"


class PaystackSaasService:
    def __init__(self):
        self.secret_key = getattr(settings, "PAYSTACK_SECRET_KEY", "") or ""
        self.base_url = "https://api.paystack.co"

    def is_configured(self) -> bool:
        return bool(self.secret_key.strip())

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    def build_reference(self, organization_id: int) -> str:
        return f"SAAS-{organization_id}-{uuid.uuid4().hex[:12].upper()}"

    def create_paystack_plan(self, plan) -> str:
        """Create or return existing Paystack plan code for monthly billing."""
        if plan.paystack_plan_code:
            return plan.paystack_plan_code

        if not self.is_configured():
            raise ValidationError("Paystack is not configured.")

        amount = plan.price_monthly
        if amount <= 0:
            raise ValidationError("Plan has no payable monthly price.")

        amount_kobo = int(amount * 100)
        payload = {
            "name": f"Damianix EMR — {plan.name}",
            "interval": "monthly",
            "amount": amount_kobo,
            "currency": (plan.currency or "NGN").upper(),
            "description": plan.description or f"{plan.name} monthly subscription",
        }

        response = requests.post(
            f"{self.base_url}/plan",
            json=payload,
            headers=self._headers(),
            timeout=30,
        )
        try:
            body = response.json()
        except ValueError:
            body = {}

        if not response.ok or not body.get("status"):
            msg = body.get("message") or response.text or "Paystack plan creation failed"
            raise ValidationError(msg)

        plan_code = body.get("data", {}).get("plan_code")
        if not plan_code:
            raise ValidationError("Paystack did not return a plan_code.")

        plan.paystack_plan_code = plan_code
        plan.save(update_fields=["paystack_plan_code", "updated_at"])
        logger.info("Created Paystack plan %s for %s", plan_code, plan.slug)
        return plan_code

    def initialize_plan_payment(
        self,
        organization,
        plan,
        reference: str,
        callback_url: Optional[str] = None,
        customer_email: Optional[str] = None,
        use_recurring: bool = True,
    ) -> Dict[str, Any]:
        if not self.is_configured():
            raise ValidationError(
                "Paystack is not configured. Set PAYSTACK_SECRET_KEY in environment."
            )

        amount = plan.price_monthly
        if amount <= 0:
            raise ValidationError("Plan has no payable monthly price.")

        amount_kobo = int(amount * 100)
        metadata = {
            "organization_id": organization.id,
            "plan_slug": plan.slug,
            "reference": reference,
            "source": SAAS_METADATA_SOURCE,
        }

        payload: Dict[str, Any] = {
            "amount": amount_kobo,
            "reference": reference,
            "currency": (plan.currency or "NGN").upper(),
            "metadata": metadata,
        }
        email = customer_email or organization.email
        if email:
            payload["email"] = email
        if callback_url:
            payload["callback_url"] = callback_url

        if use_recurring:
            try:
                plan_code = self.create_paystack_plan(plan)
                payload["plan"] = plan_code
            except ValidationError as e:
                logger.warning(
                    "Recurring plan unavailable for %s, falling back to one-time: %s",
                    plan.slug,
                    e,
                )

        response = requests.post(
            f"{self.base_url}/transaction/initialize",
            json=payload,
            headers=self._headers(),
            timeout=30,
        )
        try:
            body = response.json()
        except ValueError:
            body = {}
        if not response.ok:
            msg = body.get("message") or response.text or "Paystack initialization failed"
            raise ValidationError(msg)

        if not body.get("status"):
            raise ValidationError(body.get("message", "Paystack initialization failed"))

        return body

    def verify_transaction(self, reference: str) -> Dict[str, Any]:
        if not self.is_configured():
            raise ValidationError("Paystack is not configured.")

        response = requests.get(
            f"{self.base_url}/transaction/verify/{reference}",
            headers=self._headers(),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def disable_subscription(
        self, subscription_code: str, email_token: str
    ) -> Dict[str, Any]:
        """Disable Paystack auto-renewal for a subscription."""
        if not self.is_configured():
            raise ValidationError("Paystack is not configured.")

        response = requests.post(
            f"{self.base_url}/subscription/disable",
            json={"code": subscription_code, "token": email_token},
            headers=self._headers(),
            timeout=30,
        )
        try:
            body = response.json()
        except ValueError:
            body = {}
        if not response.ok or not body.get("status"):
            msg = body.get("message") or "Failed to disable Paystack subscription"
            raise ValidationError(msg)
        return body

    def is_successful(self, paystack_response: Dict[str, Any]) -> bool:
        if not paystack_response.get("status"):
            return False
        data = paystack_response.get("data", {})
        return (
            data.get("status") == "success"
            and data.get("gateway_response") == "Successful"
        )

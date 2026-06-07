"""
Paystack webhook handlers for SaaS subscription lifecycle events.

Handles subscription.create, subscription.disable, invoice.payment_failed,
and renewal charge.success events (in addition to initial SAAS-* checkout).
"""

import logging
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import Organization, Plan, SaasSubscriptionPayment, Subscription
from .paystack_subscription_service import SAAS_METADATA_SOURCE

logger = logging.getLogger(__name__)

SAAS_SUBSCRIPTION_EVENTS = {
    "subscription.create",
    "subscription.disable",
    "subscription.not_renew",
    "invoice.payment_failed",
    "invoice.update",
}


def handle_paystack_saas_event(event: str, data: dict) -> bool:
    """
    Process Paystack SaaS subscription webhook events.
    Returns True if the event was handled (or safely ignored).
    """
    if event == "charge.success":
        return _handle_renewal_charge_success(data)

    if event not in SAAS_SUBSCRIPTION_EVENTS:
        return False

    if event == "subscription.create":
        _handle_subscription_create(data)
        return True

    if event in ("subscription.disable", "subscription.not_renew"):
        _handle_subscription_disable(data)
        return True

    if event == "invoice.payment_failed":
        _handle_invoice_payment_failed(data)
        return True

    if event == "invoice.update":
        _handle_invoice_paid(data)
        return True

    return False


def _find_subscription_by_paystack(data: dict):
    sub_code = data.get("subscription_code") or data.get("code")
    if sub_code:
        sub = Subscription.objects.filter(
            paystack_subscription_code=sub_code
        ).select_related("organization", "plan").first()
        if sub:
            return sub

    plan_data = data.get("plan") or {}
    plan_code = plan_data.get("plan_code") if isinstance(plan_data, dict) else None
    customer = data.get("customer") or {}
    customer_email = customer.get("email") if isinstance(customer, dict) else None

    if customer_email and plan_code:
        try:
            plan = Plan.objects.get(paystack_plan_code=plan_code)
            org = Organization.objects.get(email=customer_email, is_active=True)
            return Subscription.objects.filter(
                organization=org, plan=plan
            ).select_related("organization", "plan").first()
        except (Plan.DoesNotExist, Organization.DoesNotExist):
            pass

    return None


@transaction.atomic
def _handle_subscription_create(data: dict):
    sub_code = data.get("subscription_code")
    if not sub_code:
        return

    existing = Subscription.objects.filter(
        paystack_subscription_code=sub_code
    ).first()
    if existing:
        existing.auto_renew_enabled = True
        existing.status = "ACTIVE"
        existing.save(update_fields=["auto_renew_enabled", "status", "updated_at"])
        return

    subscription = _find_subscription_by_paystack(data)
    if not subscription:
        metadata = data.get("metadata") or {}
        org_id = metadata.get("organization_id")
        if org_id:
            try:
                subscription = Subscription.objects.select_related(
                    "organization", "plan"
                ).get(organization_id=int(org_id))
            except (Subscription.DoesNotExist, ValueError):
                return
        else:
            return

    customer = data.get("customer") or {}
    subscription.paystack_subscription_code = sub_code
    if isinstance(customer, dict) and customer.get("customer_code"):
        subscription.paystack_customer_code = customer["customer_code"]
    email_token = data.get("email_token")
    if email_token:
        subscription.paystack_email_token = email_token
    subscription.auto_renew_enabled = True
    subscription.status = "ACTIVE"
    update_fields = [
        "paystack_subscription_code",
        "paystack_customer_code",
        "auto_renew_enabled",
        "status",
        "updated_at",
    ]
    if email_token:
        update_fields.append("paystack_email_token")
    subscription.save(update_fields=update_fields)
    logger.info(
        "Paystack subscription %s linked to org %s",
        sub_code,
        subscription.organization_id,
    )


@transaction.atomic
def _handle_subscription_disable(data: dict):
    sub_code = data.get("subscription_code") or data.get("code")
    if not sub_code:
        return

    try:
        subscription = Subscription.objects.get(paystack_subscription_code=sub_code)
    except Subscription.DoesNotExist:
        return

    subscription.auto_renew_enabled = False
    subscription.cancel_at_period_end = True
    subscription.save(
        update_fields=["auto_renew_enabled", "cancel_at_period_end", "updated_at"]
    )
    logger.info("Paystack subscription %s disabled for org %s", sub_code, subscription.organization_id)


@transaction.atomic
def _handle_invoice_payment_failed(data: dict):
    subscription = _find_subscription_by_paystack(data)
    if not subscription:
        return

    subscription.status = "PAST_DUE"
    subscription.save(update_fields=["status", "updated_at"])
    logger.warning(
        "SaaS subscription PAST_DUE for org %s", subscription.organization_id
    )


@transaction.atomic
def _handle_invoice_paid(data: dict):
    """Extend subscription period when Paystack invoice is paid (renewal)."""
    if data.get("paid") is not True:
        return

    subscription = _find_subscription_by_paystack(data)
    if not subscription:
        return

    now = timezone.now()
    start = subscription.current_period_end or now
    if start < now:
        start = now

    subscription.status = "ACTIVE"
    subscription.current_period_start = start
    subscription.current_period_end = start + timedelta(days=30)
    subscription.auto_renew_enabled = True
    subscription.save(
        update_fields=[
            "status",
            "current_period_start",
            "current_period_end",
            "auto_renew_enabled",
            "updated_at",
        ]
    )


def _handle_renewal_charge_success(data: dict) -> bool:
    """
    Handle charge.success for subscription renewals (no SAAS-* reference).
    Initial checkout is handled by saas_payment_handlers.
    """
    reference = data.get("reference", "")
    metadata = data.get("metadata") or {}

    if metadata.get("source") == SAAS_METADATA_SOURCE or str(reference).startswith(
        "SAAS-"
    ):
        return False

    plan_data = data.get("plan")
    if not plan_data:
        return False

    plan_code = plan_data.get("plan_code") if isinstance(plan_data, dict) else None
    if not plan_code:
        return False

    try:
        plan = Plan.objects.get(paystack_plan_code=plan_code)
    except Plan.DoesNotExist:
        return False

    customer = data.get("customer") or {}
    customer_email = customer.get("email") if isinstance(customer, dict) else None
    org = None
    if customer_email:
        org = Organization.objects.filter(email=customer_email, is_active=True).first()

    if not org:
        sub_code = data.get("subscription_code")
        if sub_code:
            sub = Subscription.objects.filter(
                paystack_subscription_code=sub_code
            ).select_related("organization").first()
            if sub:
                org = sub.organization

    if not org:
        return False

    amount_paid = Decimal(data.get("amount", 0)) / 100
    ref = reference or f"RENEW-{org.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"

    if SaasSubscriptionPayment.objects.filter(reference=ref, status="VERIFIED").exists():
        return True

    payment, created = SaasSubscriptionPayment.objects.get_or_create(
        reference=ref,
        defaults={
            "organization": org,
            "plan": plan,
            "amount": amount_paid or plan.price_monthly,
            "currency": plan.currency or "NGN",
            "provider": "PAYSTACK",
            "status": "VERIFIED",
            "customer_email": customer_email,
            "provider_transaction_id": str(data.get("id", "")),
            "verified_at": timezone.now(),
        },
    )
    if not created and payment.status != "VERIFIED":
        payment.status = "VERIFIED"
        payment.verified_at = timezone.now()
        payment.provider_transaction_id = str(data.get("id", ""))
        payment.save(
            update_fields=["status", "verified_at", "provider_transaction_id", "updated_at"]
        )

    sub, _ = Subscription.objects.get_or_create(
        organization=org,
        defaults={"plan": plan, "status": "ACTIVE"},
    )
    now = timezone.now()
    start = sub.current_period_end if sub.current_period_end and sub.current_period_end > now else now
    sub.plan = plan
    sub.status = "ACTIVE"
    sub.auto_renew_enabled = True
    sub.current_period_start = start
    sub.current_period_end = start + timedelta(days=30)
    sub.save(
        update_fields=[
            "plan",
            "status",
            "auto_renew_enabled",
            "current_period_start",
            "current_period_end",
            "updated_at",
        ]
    )
    logger.info("Paystack renewal processed for org %s ref %s", org.id, ref)
    return True

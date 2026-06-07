"""
SaaS subscription payment orchestration (Paystack / Flutterwave).
"""

import logging
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .flutterwave_subscription_service import FlutterwaveSaasService
from .models import Plan, SaasSubscriptionPayment, Subscription
from .paystack_subscription_service import PaystackSaasService, SAAS_METADATA_SOURCE

logger = logging.getLogger(__name__)


def get_saas_payment_provider() -> str:
    from django.conf import settings

    return getattr(settings, "SAAS_PAYMENT_PROVIDER", "paystack").lower()


def create_checkout_session(organization, plan_slug, success_url, cancel_url):
    """
    Initialize local payment provider checkout.
    Returns authorization URL for redirect, or None if not configured.
    """
    provider = get_saas_payment_provider()
    if provider == "manual":
        logger.warning("SAAS_PAYMENT_PROVIDER=manual — no online checkout")
        return None

    try:
        plan = Plan.objects.get(slug=plan_slug, is_active=True)
    except Plan.DoesNotExist:
        logger.warning("Plan %s not found", plan_slug)
        return None

    if plan.price_monthly <= 0:
        logger.warning("Plan %s has zero price", plan_slug)
        return None

    callback_url = success_url or cancel_url

    if provider == "flutterwave":
        return _create_flutterwave_checkout(
            organization, plan, callback_url
        )
    return _create_paystack_checkout(organization, plan, callback_url)


def _create_paystack_checkout(organization, plan, callback_url):
    service = PaystackSaasService()
    if not service.is_configured():
        return None

    reference = service.build_reference(organization.id)
    payment = SaasSubscriptionPayment.objects.create(
        organization=organization,
        plan=plan,
        reference=reference,
        amount=plan.price_monthly,
        currency=plan.currency or "NGN",
        provider="PAYSTACK",
        status="PENDING",
        customer_email=organization.email or None,
    )

    try:
        result = service.initialize_plan_payment(
            organization,
            plan,
            reference,
            callback_url=callback_url,
            customer_email=organization.email,
        )
    except Exception as e:
        payment.status = "FAILED"
        payment.failure_reason = str(e)
        payment.save(update_fields=["status", "failure_reason", "updated_at"])
        logger.exception("Paystack SaaS checkout failed: %s", e)
        return None

    data = result.get("data", {})
    auth_url = data.get("authorization_url")
    payment.authorization_url = auth_url
    payment.save(update_fields=["authorization_url", "updated_at"])
    return auth_url


def _create_flutterwave_checkout(organization, plan, callback_url):
    service = FlutterwaveSaasService()
    if not service.is_configured():
        return None

    reference = service.build_reference(organization.id)
    payment = SaasSubscriptionPayment.objects.create(
        organization=organization,
        plan=plan,
        reference=reference,
        amount=plan.price_monthly,
        currency=plan.currency or "NGN",
        provider="FLUTTERWAVE",
        status="PENDING",
        customer_email=organization.email or None,
    )

    try:
        result = service.initialize_plan_payment(
            organization,
            plan,
            reference,
            callback_url=callback_url,
            customer_email=organization.email,
        )
    except Exception as e:
        payment.status = "FAILED"
        payment.failure_reason = str(e)
        payment.save(update_fields=["status", "failure_reason", "updated_at"])
        logger.exception("Flutterwave SaaS checkout failed: %s", e)
        return None

    data = result.get("data", {})
    auth_url = data.get("link")
    payment.authorization_url = auth_url
    payment.save(update_fields=["authorization_url", "updated_at"])
    return auth_url


def verify_and_activate_subscription(reference: str) -> SaasSubscriptionPayment:
    """Verify payment with provider and upgrade organization subscription."""
    try:
        payment = SaasSubscriptionPayment.objects.select_related(
            "organization", "plan"
        ).get(reference=reference)
    except SaasSubscriptionPayment.DoesNotExist:
        raise ValidationError(f"No SaaS payment found for reference: {reference}")

    if payment.status == "VERIFIED":
        return payment

    if payment.provider == "FLUTTERWAVE":
        _verify_flutterwave_payment(payment)
    else:
        _verify_paystack_payment(payment)

    _activate_subscription(payment)
    return payment


def _verify_paystack_payment(payment: SaasSubscriptionPayment):
    service = PaystackSaasService()
    response = service.verify_transaction(payment.reference)
    if not service.is_successful(response):
        payment.status = "FAILED"
        payment.failure_reason = "Transaction not successful"
        payment.save(update_fields=["status", "failure_reason", "updated_at"])
        raise ValidationError("Paystack payment was not successful.")

    data = response.get("data", {})
    metadata = data.get("metadata") or {}
    if metadata.get("source") != SAAS_METADATA_SOURCE:
        raise ValidationError("Invalid payment metadata.")
    if int(metadata.get("organization_id", 0)) != payment.organization_id:
        raise ValidationError("Organization mismatch.")

    amount_paid = Decimal(data.get("amount", 0)) / 100
    if amount_paid < payment.amount:
        raise ValidationError("Paid amount is less than expected.")

    payment.provider_transaction_id = str(data.get("id", ""))
    payment.status = "VERIFIED"
    payment.verified_at = timezone.now()
    payment.save(
        update_fields=[
            "provider_transaction_id",
            "status",
            "verified_at",
            "updated_at",
        ]
    )


def _verify_flutterwave_payment(payment: SaasSubscriptionPayment):
    service = FlutterwaveSaasService()
    response = service.verify_transaction(payment.reference)
    if not service.is_successful(response):
        payment.status = "FAILED"
        payment.failure_reason = "Transaction not successful"
        payment.save(update_fields=["status", "failure_reason", "updated_at"])
        raise ValidationError("Flutterwave payment was not successful.")

    data = response.get("data", {})
    meta = data.get("meta") or {}
    if int(meta.get("organization_id", 0)) != payment.organization_id:
        raise ValidationError("Organization mismatch.")

    payment.provider_transaction_id = str(data.get("id", ""))
    payment.status = "VERIFIED"
    payment.verified_at = timezone.now()
    payment.save(
        update_fields=[
            "provider_transaction_id",
            "status",
            "verified_at",
            "updated_at",
        ]
    )


@transaction.atomic
def _activate_subscription(payment: SaasSubscriptionPayment):
    org = payment.organization
    now = timezone.now()
    sub, _ = Subscription.objects.get_or_create(
        organization=org,
        defaults={"plan": payment.plan, "status": "ACTIVE"},
    )
    sub.plan = payment.plan
    sub.status = "ACTIVE"
    sub.current_period_start = now
    sub.current_period_end = now + timedelta(days=30)
    sub.cancel_at_period_end = False
    if payment.plan.paystack_plan_code:
        sub.auto_renew_enabled = True
    sub.save(
        update_fields=[
            "plan",
            "status",
            "current_period_start",
            "current_period_end",
            "cancel_at_period_end",
            "auto_renew_enabled",
            "updated_at",
        ]
    )
    _notify_subscription_activated(org, payment)


def _notify_subscription_activated(org, payment: SaasSubscriptionPayment):
    from core.notifications import send_transactional_email

    to = org.email or payment.customer_email
    if not to:
        return
    end = payment.organization.subscription.current_period_end
    end_str = end.strftime("%d %b %Y") if end else "in 30 days"
    amount = f"{payment.currency} {payment.amount:,.2f}"
    send_transactional_email(
        to,
        f"Subscription upgraded — {org.name}",
        (
            f"Your clinic ({org.name}) is now on the {payment.plan.name} plan.\n\n"
            f"Amount paid: {amount}\n"
            f"Reference: {payment.reference}\n"
            f"Active until: {end_str}\n\n"
            f"Thank you for using Damianix EMR."
        ),
    )
    try:
        from .tasks import generate_and_send_invoice_pdf

        generate_and_send_invoice_pdf.delay(
            org.id,
            payment.reference,
            str(payment.amount),
            timezone.now().strftime("%Y-%m-%d"),
            "PAID",
        )
    except Exception:
        logger.debug("Celery unavailable — invoice PDF task skipped")


def handle_paystack_webhook_charge_success(data: dict) -> bool:
    """
    Process Paystack charge.success for SaaS payments.
    Returns True if handled, False to fall through to visit billing.
    """
    reference = data.get("reference")
    if not reference:
        return False

    metadata = data.get("metadata") or {}
    if metadata.get("source") != SAAS_METADATA_SOURCE and not str(
        reference
    ).startswith("SAAS-"):
        return False

    try:
        verify_and_activate_subscription(reference)
        return True
    except Exception as e:
        logger.exception("SaaS Paystack webhook failed for %s: %s", reference, e)
        return True


def get_payment_history(organization, limit=10):
    """Local invoice history from verified SaaS payments."""
    payments = SaasSubscriptionPayment.objects.filter(
        organization=organization, status="VERIFIED"
    ).select_related("plan")[:limit]

    return [
        {
            "id": p.reference,
            "number": p.reference,
            "amount_due": float(p.amount),
            "amount_paid": float(p.amount),
            "currency": p.currency,
            "status": "paid",
            "created": int(p.verified_at.timestamp()) if p.verified_at else 0,
            "hosted_invoice_url": None,
            "pdf": None,
            "plan_name": p.plan.name,
            "provider": p.provider,
        }
        for p in payments
    ]

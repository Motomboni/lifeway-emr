"""
SaaS Billing Service - subscription management and usage tracking.

Nigeria-first: Paystack or Flutterwave for plan upgrades (SAAS_PAYMENT_PROVIDER).
Legacy Stripe helpers retained only when SAAS_PAYMENT_PROVIDER=stripe.
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def get_usage_for_organization(organization):
    from apps.patients.models import Patient

    from .models import OrganizationUser

    return {
        "patients": Patient.objects.filter(organization=organization).count(),
        "users": OrganizationUser.objects.filter(organization=organization).count(),
    }


def get_subscription_status(organization):
    from django.utils import timezone

    from .models import Subscription

    usage = get_usage_for_organization(organization)
    provider = getattr(settings, "SAAS_PAYMENT_PROVIDER", "paystack")
    try:
        sub = organization.subscription
        plan = sub.plan
        days_until_renewal = None
        if sub.current_period_end:
            days_until_renewal = max(
                0, (sub.current_period_end - timezone.now()).days
            )
        return {
            "plan": {
                "name": plan.name,
                "slug": plan.slug,
                "max_users": plan.max_users,
                "max_patients": plan.max_patients,
                "price_monthly": str(plan.price_monthly),
                "currency": plan.currency,
            },
            "status": sub.status,
            "payment_provider": provider,
            "days_until_renewal": days_until_renewal,
            "current_period_end": sub.current_period_end.isoformat()
            if sub.current_period_end
            else None,
            "trial_ends_at": sub.trial_ends_at.isoformat()
            if sub.trial_ends_at
            else None,
            "auto_renew_enabled": sub.auto_renew_enabled,
            "paystack_subscription_code": sub.paystack_subscription_code,
            "usage": usage,
            "limits": {
                "users": {
                    "current": usage["users"],
                    "max": plan.max_users,
                    "at_limit": plan.max_users is not None
                    and usage["users"] >= plan.max_users,
                },
                "patients": {
                    "current": usage["patients"],
                    "max": plan.max_patients,
                    "at_limit": plan.max_patients is not None
                    and usage["patients"] >= plan.max_patients,
                },
            },
        }
    except Subscription.DoesNotExist:
        return {
            "plan": None,
            "status": "NONE",
            "payment_provider": provider,
            "days_until_renewal": None,
            "usage": usage,
            "limits": {
                "users": {"current": usage["users"], "max": None, "at_limit": False},
                "patients": {
                    "current": usage["patients"],
                    "max": None,
                    "at_limit": False,
                },
            },
        }


def create_checkout_session(organization, plan_slug, success_url, cancel_url):
    provider = getattr(settings, "SAAS_PAYMENT_PROVIDER", "paystack").lower()
    if provider == "stripe":
        return create_stripe_checkout_session(
            organization, plan_slug, success_url, cancel_url
        )
    from .saas_payment_handlers import create_checkout_session as local_checkout

    return local_checkout(organization, plan_slug, success_url, cancel_url)


def get_billing_invoices(organization, limit=10):
    provider = getattr(settings, "SAAS_PAYMENT_PROVIDER", "paystack").lower()
    if provider == "stripe":
        return get_stripe_invoices(organization, limit)
    from .saas_payment_handlers import get_payment_history

    return get_payment_history(organization, limit)


def create_billing_portal_session(organization, return_url):
    provider = getattr(settings, "SAAS_PAYMENT_PROVIDER", "paystack").lower()
    if provider == "stripe":
        return create_stripe_billing_portal_session(organization, return_url)
    return None


def create_stripe_checkout_session(organization, plan_slug, success_url, cancel_url):
    stripe_key = getattr(settings, "STRIPE_SECRET_KEY", "")
    if not stripe_key:
        return None
    try:
        import stripe

        stripe.api_key = stripe_key
        from .models import Plan

        plan = Plan.objects.get(slug=plan_slug, is_active=True)
        if not plan.stripe_price_id:
            return None
        customer_id = None
        try:
            customer_id = organization.subscription.stripe_customer_id
        except Exception:
            pass
        session_params = {
            "mode": "subscription",
            "line_items": [{"price": plan.stripe_price_id, "quantity": 1}],
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": {
                "organization_id": str(organization.id),
                "plan_slug": plan_slug,
            },
        }
        if customer_id:
            session_params["customer"] = customer_id
        else:
            session_params["customer_email"] = organization.email or None
        session = stripe.checkout.Session.create(**session_params)
        return session.get("url")
    except Exception as e:
        logger.exception("Stripe checkout failed: %s", e)
        return None


def create_stripe_billing_portal_session(organization, return_url):
    stripe_key = getattr(settings, "STRIPE_SECRET_KEY", "")
    if not stripe_key:
        return None
    try:
        import stripe

        stripe.api_key = stripe_key
        customer_id = None
        try:
            customer_id = organization.subscription.stripe_customer_id
        except Exception:
            pass
        if not customer_id:
            return None
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return session.url
    except Exception as e:
        logger.exception("Stripe portal failed: %s", e)
        return None


def get_stripe_invoices(organization, limit=10):
    stripe_key = getattr(settings, "STRIPE_SECRET_KEY", "")
    if not stripe_key:
        return []
    try:
        import stripe

        stripe.api_key = stripe_key
        customer_id = None
        try:
            customer_id = organization.subscription.stripe_customer_id
        except Exception:
            pass
        if not customer_id:
            return []
        invoices = stripe.Invoice.list(customer=customer_id, limit=limit)
        return [
            {
                "id": inv.id,
                "amount_due": inv.amount_due / 100,
                "amount_paid": inv.amount_paid / 100,
                "currency": inv.currency.upper(),
                "status": inv.status,
                "created": inv.created,
                "hosted_invoice_url": inv.hosted_invoice_url,
                "pdf": inv.invoice_pdf,
                "number": inv.number,
            }
            for inv in invoices.data
        ]
    except Exception as e:
        logger.exception("Stripe invoice fetch failed: %s", e)
        return []

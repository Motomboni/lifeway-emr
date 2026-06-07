"""
Stripe webhook handler for SaaS subscription events.

POST /api/v1/subscriptions/stripe/webhook/

Public endpoint (no auth) - verified via Stripe-Signature header.
Handles: checkout.session.completed, customer.subscription.*
"""

import logging

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Handle Stripe webhook events for subscription lifecycle.
    Verifies signature, then processes checkout.session.completed and
    customer.subscription.* events.
    """
    payload = request.body
    sig_header = request.headers.get("Stripe-Signature", "")

    webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")
    if not webhook_secret:
        logger.warning("STRIPE_WEBHOOK_SECRET not configured - rejecting webhook")
        return JsonResponse({"error": "Webhook not configured"}, status=503)

    try:
        import stripe

        stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", "")
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError as e:
        logger.warning("Stripe webhook invalid payload: %s", e)
        return JsonResponse({"error": "Invalid payload"}, status=400)
    except Exception as e:
        logger.warning("Stripe webhook signature verification failed: %s", e)
        return JsonResponse({"error": "Invalid signature"}, status=400)

    event_type = event.get("type")
    data = event.get("data", {}).get("object", {})

    try:
        if event_type == "checkout.session.completed":
            _handle_checkout_completed(data)
        elif event_type == "customer.subscription.created":
            _handle_subscription_created(data)
        elif event_type == "customer.subscription.updated":
            _handle_subscription_updated(data)
        elif event_type == "customer.subscription.deleted":
            _handle_subscription_deleted(data)
        elif event_type == "invoice.payment_succeeded":
            _handle_invoice_payment_succeeded(data)
        elif event_type == "invoice.payment_failed":
            _handle_invoice_payment_failed(data)
        else:
            logger.debug("Stripe webhook unhandled event: %s", event_type)
    except Exception as e:
        logger.exception("Stripe webhook processing error: %s", e)
        return JsonResponse({"error": "Processing failed"}, status=500)

    return JsonResponse({"received": True})


def _handle_checkout_completed(data):
    """Update subscription with Stripe IDs from checkout session."""
    from .models import Organization, Plan, Subscription

    metadata = data.get("metadata", {})
    org_id = metadata.get("organization_id")
    plan_slug = metadata.get("plan_slug")
    if not org_id:
        logger.warning("checkout.session.completed missing organization_id in metadata")
        return

    try:
        org = Organization.objects.get(pk=org_id)
    except Organization.DoesNotExist:
        logger.warning("checkout.session.completed org not found: %s", org_id)
        return

    subscription_id = data.get("subscription")
    customer_id = data.get("customer")
    default_plan = Plan.objects.filter(slug="starter").first()
    plan = Plan.objects.filter(slug=plan_slug).first() if plan_slug else default_plan

    sub, _ = Subscription.objects.get_or_create(
        organization=org, defaults={"plan": plan or default_plan, "status": "ACTIVE"}
    )
    sub.stripe_subscription_id = subscription_id
    sub.stripe_customer_id = customer_id
    sub.status = "ACTIVE"
    if plan:
        sub.plan = plan
    update_fields = ["stripe_subscription_id", "stripe_customer_id", "status"]
    if plan:
        update_fields.append("plan")
    sub.save(update_fields=update_fields)
    logger.info("Updated subscription for org %s from checkout", org_id)


def _handle_subscription_created(data):
    """Sync subscription created event (period dates)."""
    _sync_subscription_from_stripe(data)


def _handle_subscription_updated(data):
    """Sync subscription updated (plan change, period, cancel_at_period_end)."""
    _sync_subscription_from_stripe(data)


def _handle_subscription_deleted(data):
    """Mark subscription as cancelled."""
    from .models import Subscription

    stripe_sub_id = data.get("id")
    if not stripe_sub_id:
        return
    try:
        sub = Subscription.objects.get(stripe_subscription_id=stripe_sub_id)
        sub.status = "CANCELLED"
        sub.save(update_fields=["status"])
        logger.info("Marked subscription cancelled for org %s", sub.organization_id)
    except Subscription.DoesNotExist:
        logger.debug("Subscription not found for stripe id %s", stripe_sub_id)


def _sync_subscription_from_stripe(data):
    """Update our Subscription from Stripe subscription object."""
    from .models import Plan, Subscription

    stripe_sub_id = data.get("id")
    if not stripe_sub_id:
        return

    try:
        sub = Subscription.objects.get(stripe_subscription_id=stripe_sub_id)
    except Subscription.DoesNotExist:
        logger.debug("Subscription not found for stripe id %s", stripe_sub_id)
        return

    # Period
    start_ts = data.get("current_period_start")
    end_ts = data.get("current_period_end")
    if start_ts:
        sub.current_period_start = timezone.datetime.fromtimestamp(
            start_ts, tz=timezone.utc
        )
    if end_ts:
        sub.current_period_end = timezone.datetime.fromtimestamp(
            end_ts, tz=timezone.utc
        )

    # Status mapping
    stripe_status = data.get("status", "")
    status_map = {
        "active": "ACTIVE",
        "trialing": "TRIAL",
        "past_due": "PAST_DUE",
        "canceled": "CANCELLED",
        "unpaid": "PAST_DUE",
    }
    sub.status = status_map.get(stripe_status, sub.status)

    # Cancel at period end
    sub.cancel_at_period_end = bool(data.get("cancel_at_period_end"))
    cancel_at = data.get("cancel_at")
    if cancel_at:
        sub.cancel_at = timezone.datetime.fromtimestamp(cancel_at, tz=timezone.utc)
    else:
        sub.cancel_at = None

    # Plan from price
    items = data.get("items", {}).get("data", [])
    if items:
        price_id = items[0].get("price", {}).get("id")
        plan = (
            Plan.objects.filter(stripe_price_id=price_id).first()
            or Plan.objects.filter(stripe_price_id_yearly=price_id).first()
        )
        if plan:
            sub.plan = plan

    sub.save()
    logger.info("Synced subscription %s from Stripe", stripe_sub_id)


def _handle_invoice_payment_succeeded(data):
    """Handle successful invoice payment (could schedule Celery PDF generation)."""
    from .models import Subscription
    from .tasks import generate_and_send_invoice_pdf

    customer_id = data.get("customer")
    invoice_id = data.get("id")
    amount_paid = data.get("amount_paid", 0) / 100.0  # Convert cents
    date = data.get("created")
    if date:
        date_str = timezone.datetime.fromtimestamp(date, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    else:
        date_str = "Unknown Date"

    try:
        sub = Subscription.objects.select_related("organization").get(stripe_customer_id=customer_id)
        # Update status if needed, but 'customer.subscription.updated' usually handles it.
        # Call Celery task for PDF Invoice generation
        generate_and_send_invoice_pdf.delay(
            sub.organization.id,
            invoice_id,
            amount_paid,
            date_str,
            "PAID"
        )
        logger.info("Queued PDF Invoice generation for org %s, invoice %s", sub.organization.id, invoice_id)
    except Subscription.DoesNotExist:
        logger.debug("Subscription not found for stripe customer %s during invoice.payment_succeeded", customer_id)


def _handle_invoice_payment_failed(data):
    """Handle failed invoice payment (could trigger warning emails to organization admins)."""
    from .models import Subscription

    customer_id = data.get("customer")
    invoice_id = data.get("id")

    try:
        sub = Subscription.objects.select_related("organization").get(stripe_customer_id=customer_id)
        # Mark subscription as past due (though 'customer.subscription.updated' normally does this as well).
        if sub.status != "PAST_DUE":
            sub.status = "PAST_DUE"
            sub.save(update_fields=["status"])
        logger.warning("Invoice %s payment failed for org %s. Set to PAST_DUE", invoice_id, sub.organization_id)
        # We could also use Celery to send a past-due email alert here.
    except Subscription.DoesNotExist:
        logger.debug("Subscription not found for stripe customer %s during invoice.payment_failed", customer_id)


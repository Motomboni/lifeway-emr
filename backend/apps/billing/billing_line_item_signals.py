"""
Django Signals for BillingLineItem model.

Per EMR Rules:
- Fire PAYMENT_CONFIRMED event when BillingLineItem transitions to PAID
- Ensure idempotency (no double-triggering)
- Clean separation of concerns
"""
import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction

from .billing_line_item_models import BillingLineItem
from .domain_events import PaymentConfirmedEvent
from .payment_event_handlers import handle_payment_confirmed_idempotent

logger = logging.getLogger(__name__)


# Track previous state to detect transitions
_previous_bill_status = {}


@receiver(pre_save, sender=BillingLineItem)
def track_billing_line_item_status_change(sender, instance, **kwargs):
    """
    Track bill_status before save to detect transitions.
    
    This allows us to detect when status changes from non-PAID to PAID.
    """
    if instance.pk:
        try:
            old_instance = BillingLineItem.objects.get(pk=instance.pk)
            _previous_bill_status[instance.pk] = old_instance.bill_status
        except BillingLineItem.DoesNotExist:
            _previous_bill_status[instance.pk] = None
    else:
        # New instance
        _previous_bill_status[instance.pk] = None


@receiver(post_save, sender=BillingLineItem)
def handle_billing_line_item_payment_confirmed(sender, instance, created, **kwargs):
    """
    Fire PAYMENT_CONFIRMED event when BillingLineItem transitions to PAID.
    
    This signal handler:
    1. Detects transition from non-PAID to PAID
    2. Fires PAYMENT_CONFIRMED event
    3. Ensures idempotency (only fires on actual transition)
    
    Args:
        sender: BillingLineItem model class
        instance: BillingLineItem instance
        created: Whether instance was just created
        **kwargs: Additional signal arguments
    """
    # Get previous status
    previous_status = _previous_bill_status.get(instance.pk)
    
    # Clean up tracking
    if instance.pk in _previous_bill_status:
        del _previous_bill_status[instance.pk]
    
    # Check if status transitioned to PAID
    transitioned_to_paid = (
        instance.bill_status == 'PAID' and
        previous_status != 'PAID'
    )
    
    if not transitioned_to_paid:
        # No transition to PAID - nothing to do
        return
    
    logger.info(
        f"BillingLineItem {instance.id} transitioned to PAID "
        f"(previous status: {previous_status})"
    )
    
    # Fire PAYMENT_CONFIRMED event
    try:
        event = PaymentConfirmedEvent(
            billing_line_item_id=instance.id,
            visit_id=instance.visit.id,
            service_code=instance.source_service_code,
            amount=instance.amount,
            payment_method=instance.payment_method or 'CASH',
            consultation_id=instance.consultation.id if instance.consultation else None,
        )
        
        # Handle event (idempotent)
        # Use transaction to ensure atomicity
        with transaction.atomic():
            handle_payment_confirmed_idempotent(event)
        
        logger.info(
            f"Successfully fired PAYMENT_CONFIRMED event for BillingLineItem {instance.id}"
        )
    except Exception as e:
        # Log error but don't fail the save
        # This ensures billing line item is saved even if event handling fails
        logger.error(
            f"Error firing PAYMENT_CONFIRMED event for BillingLineItem {instance.id}: {str(e)}",
            exc_info=True
        )


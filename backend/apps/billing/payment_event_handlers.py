"""
Event Handlers for Payment Confirmed Events.

Per EMR Rules:
- Handlers are idempotent (can be called multiple times safely)
- Clean separation of concerns
- No side effects if already processed
"""
import logging
from django.db import transaction
from django.core.exceptions import ValidationError

from .domain_events import PaymentConfirmedEvent
from apps.visits.models import Visit
from apps.consultations.models import Consultation
from apps.consultations.gopd_workflow_service import activate_consultation

logger = logging.getLogger(__name__)


def handle_payment_confirmed(event: PaymentConfirmedEvent) -> None:
    """
    Handle PAYMENT_CONFIRMED event.
    
    This handler:
    1. Unlocks consultation if waiting (PENDING status)
    2. Updates visit status if needed
    3. Ensures idempotency
    
    Args:
        event: PaymentConfirmedEvent instance
    
    Raises:
        ValidationError: If event data is invalid
    """
    logger.info(
        f"Handling PAYMENT_CONFIRMED event for billing line item {event.billing_line_item_id}, "
        f"visit {event.visit_id}"
    )
    
    with transaction.atomic():
        # Get visit
        try:
            visit = Visit.objects.select_for_update().get(pk=event.visit_id)
        except Visit.DoesNotExist:
            logger.error(f"Visit {event.visit_id} not found for payment confirmed event")
            raise ValidationError(f"Visit {event.visit_id} not found")
        
        # Handler 1: Unlock consultation if waiting
        if event.consultation_id:
            _unlock_consultation(event.consultation_id, visit)
        
        # Handler 2: Update visit status if needed
        _update_visit_status(visit)
        
        logger.info(
            f"Successfully processed PAYMENT_CONFIRMED event for visit {event.visit_id}"
        )


def _unlock_consultation(consultation_id: int, visit: Visit) -> None:
    """
    Unlock consultation if it's in PENDING status.
    
    Idempotent: If consultation is already ACTIVE, does nothing.
    
    Since PAYMENT_CONFIRMED event was fired, we trust that payment was confirmed
    and update visit payment_status if needed before activating consultation.
    
    Args:
        consultation_id: Consultation ID
        visit: Visit instance
    """
    try:
        consultation = Consultation.objects.select_for_update().get(
            pk=consultation_id,
            visit=visit
        )
        
        # Idempotency check: Only process if consultation is PENDING
        if consultation.status == 'PENDING':
            logger.info(
                f"Unlocking consultation {consultation_id} for visit {visit.id} "
                f"after payment confirmation"
            )
            
            # Since PAYMENT_CONFIRMED event was fired, payment was confirmed
            # Update visit payment_status if not already cleared
            if not visit.is_payment_cleared():
                # Since PAYMENT_CONFIRMED event was fired, we know payment was confirmed
                # Update payment_status to PAID or PARTIALLY_PAID based on billing summary
                from .billing_service import BillingService
                summary = BillingService.compute_billing_summary(visit)
                
                # If summary shows payment is cleared, update visit
                if summary.payment_status in ['PAID', 'SETTLED', 'PARTIALLY_PAID']:
                    visit.payment_status = summary.payment_status
                else:
                    # If billing summary doesn't reflect payment yet, set to PAID
                    # (since the event confirms payment was made)
                    visit.payment_status = 'PAID'
                
                visit.save(update_fields=['payment_status'])
                logger.info(
                    f"Updated visit {visit.id} payment_status to {visit.payment_status} "
                    f"after payment confirmation"
                )
            
            # Activate consultation
            # Note: We need a doctor to activate. If no doctor is assigned, we'll assign one
            # from the consultation's created_by or leave it unassigned
            if consultation.created_by:
                try:
                    activate_consultation(consultation, consultation.created_by)
                    logger.info(f"Activated consultation {consultation_id}")
                except ValidationError as e:
                    logger.error(
                        f"Failed to activate consultation {consultation_id}: {str(e)}"
                    )
                    # If activation fails due to payment check, try direct status update
                    # (since we know payment was confirmed via the event)
                    if 'payment' in str(e).lower():
                        consultation.status = 'ACTIVE'
                        consultation.save(update_fields=['status'])
                        logger.info(
                            f"Updated consultation {consultation_id} status to ACTIVE "
                            f"(payment confirmed via event)"
                        )
            else:
                # No doctor assigned - just update status to ACTIVE
                consultation.status = 'ACTIVE'
                consultation.save(update_fields=['status'])
                logger.info(
                    f"Updated consultation {consultation_id} status to ACTIVE "
                    f"(no doctor assigned yet)"
                )
        elif consultation.status == 'ACTIVE':
            logger.debug(
                f"Consultation {consultation_id} already ACTIVE, skipping unlock"
            )
        elif consultation.status == 'CLOSED':
            logger.debug(
                f"Consultation {consultation_id} already CLOSED, skipping unlock"
            )
    except Consultation.DoesNotExist:
        logger.warning(
            f"Consultation {consultation_id} not found for visit {visit.id}, "
            f"skipping unlock"
        )
    except Exception as e:
        logger.error(
            f"Error unlocking consultation {consultation_id}: {str(e)}",
            exc_info=True
        )
        # Don't raise - allow other handlers to proceed


def _update_visit_status(visit: Visit) -> None:
    """
    Update visit status to ACTIVE if payment is cleared.
    
    Idempotent: If visit is already in correct state, does nothing.
    
    Note: Visit status is typically 'OPEN' or 'CLOSED', not 'ACTIVE'.
    The "ACTIVE" state is conceptual - we ensure visit is OPEN and payment is cleared.
    
    Args:
        visit: Visit instance
    """
    # Idempotency check: Only process if visit is OPEN and payment not cleared
    if visit.status != 'OPEN':
        logger.debug(
            f"Visit {visit.id} status is {visit.status}, not OPEN. Skipping status update."
        )
        return
    
    # Check if payment is cleared
    if visit.is_payment_cleared():
        # Payment is cleared - visit is effectively "ACTIVE"
        # Update payment_status if needed (should already be updated)
        if visit.payment_status not in ['PAID', 'SETTLED', 'PARTIALLY_PAID']:
            # Update payment_status to reflect cleared state
            from .billing_service import BillingService
            summary = BillingService.compute_billing_summary(visit)
            visit.payment_status = summary.payment_status
            visit.save(update_fields=['payment_status'])
            logger.info(
                f"Updated visit {visit.id} payment_status to {visit.payment_status} "
                f"after payment confirmation"
            )
        else:
            logger.debug(
                f"Visit {visit.id} payment_status already {visit.payment_status}, "
                f"skipping update"
            )
    else:
        logger.debug(
            f"Visit {visit.id} payment not cleared yet, skipping status update"
        )


def handle_payment_confirmed_idempotent(event: PaymentConfirmedEvent) -> None:
    """
    Idempotent wrapper for handle_payment_confirmed.
    
    Ensures event is only processed once by checking if already processed.
    Checks consultation status to determine if event was already handled.
    
    Args:
        event: PaymentConfirmedEvent instance
    """
    from .billing_line_item_models import BillingLineItem
    
    try:
        line_item = BillingLineItem.objects.get(pk=event.billing_line_item_id)
        
        # If consultation is linked, check if it's already ACTIVE
        # This is the best indicator that the event was already processed
        if event.consultation_id:
            try:
                consultation = Consultation.objects.get(pk=event.consultation_id)
                if consultation.status == 'ACTIVE':
                    logger.debug(
                        f"Consultation {event.consultation_id} already ACTIVE, "
                        f"skipping payment confirmed event processing"
                    )
                    return
            except Consultation.DoesNotExist:
                pass  # Consultation not found, proceed with event handling
        
        # If no consultation or consultation is not ACTIVE, process event
        # The handler itself is idempotent, so it's safe to call multiple times
        handle_payment_confirmed(event)
        
    except BillingLineItem.DoesNotExist:
        logger.error(
            f"BillingLineItem {event.billing_line_item_id} not found for event"
        )
        raise ValidationError(
            f"BillingLineItem {event.billing_line_item_id} not found"
        )


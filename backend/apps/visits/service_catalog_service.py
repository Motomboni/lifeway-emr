"""
Service-layer functions for creating/attaching visits from ServiceCatalog.

Per EMR Rules:
- Services drive workflows, not just pricing
- If service.requires_visit = true and no active visit exists, create a Visit
- One active visit per patient at a time
- Visit lifecycle is enforced
- Visit creation must be atomic and transactional
"""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from typing import Optional, Tuple
from decimal import Decimal

from .models import Visit
from apps.billing.service_catalog_models import ServiceCatalog
from apps.patients.models import Patient


# Mapping from ServiceCatalog workflow_type to Visit visit_type
WORKFLOW_TO_VISIT_TYPE_MAP = {
    'GOPD_CONSULT': 'CONSULTATION',
    'LAB_ORDER': 'ROUTINE',
    'DRUG_DISPENSE': 'ROUTINE',
    'PROCEDURE': 'ROUTINE',
    'RADIOLOGY_STUDY': 'ROUTINE',
    'INJECTION': 'ROUTINE',
    'DRESSING': 'ROUTINE',
    'VACCINATION': 'ROUTINE',
    'PHYSIOTHERAPY': 'ROUTINE',
    'OTHER': 'ROUTINE',
}


def get_or_create_visit_for_service(
    patient: Patient,
    service: ServiceCatalog,
    user=None,
    payment_type: str = 'CASH',
    chief_complaint: Optional[str] = None,
) -> Tuple[Visit, bool]:
    """
    Get existing active visit or create a new visit for a service.
    
    This function implements the service-driven visit creation logic:
    - If service.requires_visit = true and no active visit exists, create a Visit
    - Ensures one active visit per patient at a time
    - Visit creation is atomic and transactional
    - Visit lifecycle is enforced
    
    Args:
        patient: Patient instance
        service: ServiceCatalog instance
        user: User creating the visit (optional, for audit)
        payment_type: Payment type ('CASH' or 'INSURANCE'), default 'CASH'
        chief_complaint: Chief complaint for the visit (optional)
    
    Returns:
        Tuple of (Visit, created) where created is True if visit was created
    
    Raises:
        ValidationError: If service validation fails or visit creation fails
    """
    # Validate service
    if not service.is_active:
        raise ValidationError(f"Service '{service.service_code}' is not active.")
    
    # If service doesn't require a visit, return None (no visit needed)
    if not service.requires_visit:
        raise ValidationError(
            "This service does not require a visit. "
            "Use a different method to process services that don't require visits."
        )
    
    # Use transaction to ensure atomicity
    with transaction.atomic():
        # Check for existing active visit
        # Active visit = status='OPEN' and not closed
        active_visit = Visit.objects.filter(
            patient=patient,
            status='OPEN'
        ).select_for_update().first()
        
        if active_visit:
            # Use existing active visit
            # Validate that the existing visit is compatible with the service
            if service.requires_consultation and not active_visit.has_consultation():
                # Service requires consultation but visit doesn't have one yet
                # This is okay - consultation can be created later
                pass
            
            return active_visit, False
        
        # No active visit exists - create a new one
        # Map workflow_type to visit_type
        visit_type = WORKFLOW_TO_VISIT_TYPE_MAP.get(
            service.workflow_type,
            'ROUTINE'
        )
        
        # Determine initial payment_status based on service billing configuration
        # If auto_bill=True and bill_timing=BEFORE, payment is required before service
        # Otherwise, payment can be processed after service delivery
        initial_payment_status = 'UNPAID'
        
        # Note: Visit status is always 'OPEN' for new visits
        # The "service status" (AWAITING_PAYMENT, ACTIVE, COMPLETED) is determined by:
        # - AWAITING_PAYMENT: status='OPEN' and payment_status='UNPAID' and service requires payment before
        # - ACTIVE: status='OPEN' and (payment_status in ['PAID', 'PARTIALLY_PAID'] or service doesn't require payment before)
        # - COMPLETED: status='CLOSED'
        
        # Create visit
        visit = Visit.objects.create(
            patient=patient,
            visit_type=visit_type,
            status='OPEN',  # All new visits start as OPEN
            payment_type=payment_type,
            payment_status=initial_payment_status,
            chief_complaint=chief_complaint or '',
        )
        
        return visit, True


def ensure_visit_for_service(
    patient: Patient,
    service: ServiceCatalog,
    user=None,
    payment_type: str = 'CASH',
    chief_complaint: Optional[str] = None,
) -> Visit:
    """
    Ensure a visit exists for a service (get existing or create new).
    
    This is a convenience wrapper around get_or_create_visit_for_service
    that always returns a Visit (never None).
    
    Args:
        patient: Patient instance
        service: ServiceCatalog instance
        user: User creating the visit (optional, for audit)
        payment_type: Payment type ('CASH' or 'INSURANCE'), default 'CASH'
        chief_complaint: Chief complaint for the visit (optional)
    
    Returns:
        Visit instance (existing or newly created)
    
    Raises:
        ValidationError: If service validation fails or visit creation fails
    """
    visit, created = get_or_create_visit_for_service(
        patient=patient,
        service=service,
        user=user,
        payment_type=payment_type,
        chief_complaint=chief_complaint,
    )
    
    return visit


def can_order_service(service: ServiceCatalog, user_role: str) -> bool:
    """
    Check if a user with the given role can order a service.
    
    Args:
        service: ServiceCatalog instance
        user_role: User's role (e.g., 'DOCTOR', 'NURSE')
    
    Returns:
        bool: True if user can order this service
    """
    return service.can_be_ordered_by(user_role)


def validate_service_for_visit(service: ServiceCatalog, visit: Visit) -> None:
    """
    Validate that a service can be used with a visit.
    
    Args:
        service: ServiceCatalog instance
        visit: Visit instance
    
    Raises:
        ValidationError: If service cannot be used with this visit
    """
    if not service.is_active:
        raise ValidationError(f"Service '{service.service_code}' is not active.")
    
    if service.requires_visit and visit.status != 'OPEN':
        raise ValidationError(
            f"Service '{service.service_code}' requires an active visit, "
            f"but visit {visit.id} is {visit.status}."
        )
    
    if service.requires_consultation and not visit.has_consultation():
        raise ValidationError(
            f"Service '{service.service_code}' requires a consultation, "
            f"but visit {visit.id} does not have one yet."
        )


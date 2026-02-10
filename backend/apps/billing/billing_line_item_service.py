"""
Service functions for creating and managing BillingLineItems from ServiceCatalog.

Per EMR Rules:
- Every billable service creates exactly one BillingLineItem
- BillingLineItem is generated from ServiceCatalog
- Amount is snapshotted at time of billing
- Billing is immutable once paid
- When a Payment is recorded, it is allocated to line items (Registration first, then Consultation, then others)
"""
from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from typing import Optional, Tuple, List

from .billing_line_item_models import BillingLineItem
from .service_catalog_models import ServiceCatalog
from apps.visits.models import Visit
from apps.consultations.models import Consultation


def create_billing_line_item_from_service(
    service: ServiceCatalog,
    visit: Visit,
    consultation: Optional[Consultation] = None,
    created_by=None,
) -> BillingLineItem:
    """
    Create a BillingLineItem from a ServiceCatalog service.
    
    This function ensures:
    - Exactly one BillingLineItem per service per visit
    - Amount is snapshotted from ServiceCatalog
    - Service details are preserved
    
    Args:
        service: ServiceCatalog instance
        visit: Visit instance
        consultation: Consultation instance (optional, for consultation services)
        created_by: User creating the billing line item (optional)
    
    Returns:
        BillingLineItem instance
    
    Raises:
        ValidationError: If service is not active, visit is closed, or item already exists
    """
    # Validate service
    if not service.is_active:
        raise ValidationError(f"Service '{service.service_code}' is not active.")
    
    # Validate visit
    if visit.status == 'CLOSED':
        raise ValidationError("Cannot create billing line items for a CLOSED visit.")
    
    # Check if billing line item already exists
    existing = BillingLineItem.objects.filter(
        service_catalog=service,
        visit=visit
    ).first()
    
    if existing:
        raise ValidationError(
            f"Billing line item already exists for service '{service.service_code}' "
            f"and visit {visit.id}. Each service can only create one billing line item per visit."
        )
    
    # Validate consultation relationship
    if consultation:
        if consultation.visit != visit:
            raise ValidationError(
                "Consultation must belong to the same visit."
            )
        
        # Consultation can be linked to GOPD_CONSULT and consultation-dependent downstream services
        allowed_workflow_types = ['GOPD_CONSULT', 'LAB_ORDER', 'DRUG_DISPENSE', 'PROCEDURE', 'RADIOLOGY_STUDY']
        if service.workflow_type not in allowed_workflow_types:
            raise ValidationError(
                f"Consultation can only be linked to {', '.join(allowed_workflow_types)} services. "
                f"Service workflow_type: {service.workflow_type}"
            )
    
    # Create billing line item with snapshot
    with transaction.atomic():
        billing_line_item = BillingLineItem.objects.create(
            service_catalog=service,
            visit=visit,
            consultation=consultation,
            source_service_code=service.service_code,
            source_service_name=service.name,
            amount=service.amount,  # Snapshot amount
            created_by=created_by,
        )
    
    return billing_line_item


def get_or_create_billing_line_item(
    service: ServiceCatalog,
    visit: Visit,
    consultation: Optional[Consultation] = None,
    created_by=None,
) -> Tuple[BillingLineItem, bool]:
    """
    Get existing or create new BillingLineItem from ServiceCatalog.
    
    Args:
        service: ServiceCatalog instance
        visit: Visit instance
        consultation: Consultation instance (optional)
        created_by: User creating the billing line item (optional)
    
    Returns:
        Tuple of (BillingLineItem, created) where created is True if item was created
    """
    # Try to get existing item
    existing = BillingLineItem.objects.filter(
        service_catalog=service,
        visit=visit
    ).first()
    
    if existing:
        return existing, False
    
    # Create new item
    billing_line_item = create_billing_line_item_from_service(
        service=service,
        visit=visit,
        consultation=consultation,
        created_by=created_by,
    )
    
    return billing_line_item, True


def apply_payment_to_line_item(
    billing_line_item: BillingLineItem,
    payment_amount: Decimal,
    payment_method: str,
) -> BillingLineItem:
    """
    Apply payment to a BillingLineItem.

    Args:
        billing_line_item: BillingLineItem instance
        payment_amount: Payment amount
        payment_method: Payment method (CASH, WALLET, HMO, PAYSTACK)

    Returns:
        Updated BillingLineItem instance

    Raises:
        ValidationError: If item is immutable or payment is invalid
    """
    if billing_line_item.is_immutable():
        raise ValidationError("Cannot apply payment to a PAID billing line item.")

    billing_line_item.apply_payment(payment_amount, payment_method)

    return billing_line_item


def _allocation_order_key(item: BillingLineItem) -> Tuple[int, str]:
    """
    Order for allocating payment: Registration (0), Consultation (1), others (2).
    Second key is created_at for stable ordering.
    """
    sc = item.service_catalog
    name = (item.source_service_name or "").upper()
    code = (getattr(sc, "service_code", None) or "").upper()
    if getattr(sc, "restricted_service_flag", False) and (
        code.startswith("REG") or "REGISTRATION" in name
    ):
        return (0, str(item.created_at))
    if (
        getattr(sc, "department", None) == "CONSULTATION"
        and getattr(sc, "workflow_type", None) == "GOPD_CONSULT"
        and "REGISTRATION" not in name
    ):
        return (1, str(item.created_at))
    return (2, str(item.created_at))


def allocate_payment_to_line_items(
    visit: Visit,
    amount: Decimal,
    payment_method: str,
) -> List[BillingLineItem]:
    """
    Allocate a payment amount to pending BillingLineItems for a visit.
    Order: Registration first, then Consultation (GOPD), then others.
    Updates amount_paid and bill_status (PAID/PARTIALLY_PAID) so payment gates work.

    Args:
        visit: Visit instance
        amount: Total payment amount to allocate
        payment_method: CASH, WALLET, HMO, PAYSTACK

    Returns:
        List of BillingLineItem instances that were updated
    """
    if amount <= 0:
        return []

    pending = list(
        BillingLineItem.objects.filter(visit=visit)
        .exclude(bill_status="PAID")
        .select_related("service_catalog")
        .order_by("created_at")
    )
    if not pending:
        return []

    pending.sort(key=_allocation_order_key)
    updated: List[BillingLineItem] = []
    remaining = amount

    with transaction.atomic():
        for item in pending:
            if remaining <= 0:
                break
            outstanding = item.outstanding_amount
            if outstanding <= 0:
                continue
            to_apply = min(remaining, outstanding)
            item.apply_payment(to_apply, payment_method)
            updated.append(item)
            remaining -= to_apply

    return updated


def get_visit_billing_summary(visit: Visit) -> dict:
    """
    Get billing summary for a visit from BillingLineItems.
    
    Args:
        visit: Visit instance
    
    Returns:
        dict with billing summary:
        - total_amount: Sum of all billing line items
        - total_paid: Sum of all payments
        - outstanding_balance: Total outstanding
        - line_items: List of billing line items
        - status: Overall status (PENDING, PARTIALLY_PAID, PAID)
    """
    line_items = BillingLineItem.objects.filter(visit=visit)
    
    total_amount = sum(item.amount for item in line_items)
    total_paid = sum(item.amount_paid for item in line_items)
    outstanding_balance = total_amount - total_paid
    
    # Determine overall status
    if outstanding_balance <= 0:
        status = 'PAID'
    elif total_paid > 0:
        status = 'PARTIALLY_PAID'
    else:
        status = 'PENDING'
    
    return {
        'total_amount': total_amount,
        'total_paid': total_paid,
        'outstanding_balance': outstanding_balance,
        'status': status,
        'line_items': list(line_items.values(
            'id',
            'source_service_code',
            'source_service_name',
            'amount',
            'amount_paid',
            'outstanding_amount',
            'bill_status',
            'payment_method',
        )),
    }


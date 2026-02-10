"""
EMR Compliance Checker - Validates against EMR Context Document v2.

Per EMR Context Document v2 (LOCKED):
- All clinical actions MUST originate from ServiceCatalog
- Service-Driven, Visit-Scoped, Consultation-Dependent
- Strict governance rules enforcement
"""
from django.core.exceptions import ValidationError
from typing import Optional


def validate_service_catalog_origin(action_type: str, service_catalog_id: Optional[int] = None) -> None:
    """
    Validate that an action originates from ServiceCatalog.
    
    Per EMR Context Document v2: "All clinical and operational actions MUST originate from a ServiceCatalog entry."
    
    Args:
        action_type: Type of action (e.g., 'LAB_ORDER', 'PRESCRIPTION', 'PROCEDURE')
        service_catalog_id: ServiceCatalog ID (optional, for validation)
    
    Raises:
        ValidationError: If action does not originate from ServiceCatalog
    """
    if service_catalog_id is None:
        raise ValidationError(
            f"{action_type} must originate from a ServiceCatalog entry. "
            "Per EMR Context Document v2, all clinical and operational actions MUST originate from ServiceCatalog. "
            "Please select a service from the ServiceCatalog before performing this action."
        )


def validate_visit_consultation_chain(visit, consultation=None, action_type: str = "Action") -> None:
    """
    Validate the Visit → Consultation chain.
    
    Per EMR Context Document v2:
    - No Visit → No Consultation
    - No Consultation → No Lab / Radiology / Drug / Procedure Orders
    
    Args:
        visit: Visit instance (required)
        consultation: Consultation instance (optional, required for consultation-dependent actions)
        action_type: Type of action for error messages
    
    Raises:
        ValidationError: If chain is broken
    """
    if visit is None:
        raise ValidationError(
            f"{action_type} requires a Visit. "
            "Per EMR Context Document v2, all clinical actions are visit-scoped. "
            "Please ensure a visit exists before performing this action."
        )
    
    if consultation is None:
        raise ValidationError(
            f"{action_type} requires a Consultation. "
            "Per EMR Context Document v2, all orders (Lab/Radiology/Drug/Procedure) require consultation context. "
            "Please ensure a consultation exists for this visit."
        )
    
    # Validate consultation belongs to visit
    if consultation.visit_id != visit.id:
        raise ValidationError(
            f"Consultation does not belong to the specified Visit. "
            "Per EMR Context Document v2, consultations are strictly visit-scoped. "
            "Consultation ID: %(consultation_id)s belongs to Visit ID: %(visit_id)s, "
            "but this action is for Visit ID: %(current_visit_id)s."
        ) % {
            'consultation_id': consultation.id,
            'visit_id': consultation.visit_id,
            'current_visit_id': visit.id,
        }


def validate_order_result_chain(order, result_type: str = "Result") -> None:
    """
    Validate the Order → Result chain.
    
    Per EMR Context Document v2: "No Order → No Result / Report"
    
    Args:
        order: Order instance (LabOrder, RadiologyOrder, etc.)
        result_type: Type of result for error messages
    
    Raises:
        ValidationError: If order is not active
    """
    if order is None:
        raise ValidationError(
            f"{result_type} requires an active order. "
            "Per EMR Context Document v2, results can only be posted for active orders. "
            "Please ensure an active order exists before posting results."
        )
    
    # Check if order is active (status-dependent)
    if hasattr(order, 'status'):
        # LabOrder: ORDERED or SAMPLE_COLLECTED
        if hasattr(order, 'Status') and hasattr(order.Status, 'ORDERED'):
            if order.status not in [order.Status.ORDERED, getattr(order.Status, 'SAMPLE_COLLECTED', None)]:
                raise ValidationError(
                    f"{result_type} can only be posted for active orders. "
                    f"Current order status: '{order.status}'. Order ID: {order.id}. "
                    "Please ensure the order is in an active status before posting results."
                )
        # RadiologyOrder: ORDERED or PERFORMED
        elif order.status not in ['ORDERED', 'PERFORMED', 'IN_PROGRESS']:
            raise ValidationError(
                f"{result_type} can only be posted for active orders. "
                f"Current order status: '{order.status}'. Order ID: {order.id}. "
                "Please ensure the order is in ORDERED, IN_PROGRESS, or PERFORMED status before posting results."
            )


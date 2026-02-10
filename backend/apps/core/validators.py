"""
Custom Django Validators for EMR Governance Rules.

Per Nigerian Clinic Operational Realities:
- Strict enforcement of clinical workflows
- Payment clearance requirements
- Emergency override mechanisms
- Clear, actionable error messages
"""
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_consultation_required(value):
    """
    Validator: Consultation is required for LabOrder.
    
    Nigerian Clinic Rule: All lab orders must have clinical context from consultation.
    """
    if value is None:
        raise ValidationError(
            _("Lab orders require a consultation. Please ensure a consultation exists for this visit."),
            code='consultation_required',
        )


def validate_visit_required(value):
    """
    Validator: Visit is required for Consultation.
    
    Nigerian Clinic Rule: Consultations cannot exist without a visit context.
    """
    if value is None:
        raise ValidationError(
            _("Consultations require a visit. Please create a visit first."),
            code='visit_required',
        )


def validate_active_lab_order(value):
    """
    Validator: LabResult can only be posted for active LabOrder.
    
    Nigerian Clinic Rule: Results can only be posted for orders that are in ORDERED or SAMPLE_COLLECTED status.
    
    Note: This validator is called during model clean(), where value is the LabOrder instance.
    """
    if value is None:
        raise ValidationError(
            _("Lab result requires an active lab order."),
            code='active_order_required',
        )
    
    # Check if lab order exists and is active
    # Value is the LabOrder instance when called from LabResult.clean()
    if hasattr(value, 'status'):
        if value.status not in ['ORDERED', 'SAMPLE_COLLECTED']:
            raise ValidationError(
                _(
                    "Lab results can only be posted for active lab orders. "
                    "Current order status: %(status)s. Order ID: %(order_id)s. "
                    "Please ensure the lab order is in ORDERED or SAMPLE_COLLECTED status before posting results."
                ) % {
                    'status': value.status,
                    'order_id': value.id if hasattr(value, 'id') else 'N/A',
                },
                code='inactive_order',
            )


def validate_active_radiology_request(value):
    """
    Validator: Radiology report can only be posted for active RadiologyRequest.
    
    Nigerian Clinic Rule: Reports can only be posted for requests that are in PENDING or IN_PROGRESS status.
    
    Note: This validator is called during model clean(), where value is the RadiologyRequest instance.
    """
    if value is None:
        raise ValidationError(
            _("Radiology report requires an active radiology request."),
            code='active_request_required',
        )
    
    # Check if radiology request exists and is active
    # Value is the RadiologyRequest instance when called from report posting
    if hasattr(value, 'status'):
        if value.status not in ['PENDING', 'IN_PROGRESS']:
            raise ValidationError(
                _(
                    "Radiology reports can only be posted for active radiology requests. "
                    "Current request status: %(status)s. Request ID: %(request_id)s. "
                    "Please ensure the radiology request is in PENDING or IN_PROGRESS status before posting reports."
                ) % {
                    'status': value.status,
                    'request_id': value.id if hasattr(value, 'id') else 'N/A',
                },
                code='inactive_request',
            )


def validate_prescription_dispensing(value, emergency_override=False):
    """
    Validator: Prescription can only be dispensed if billing is paid (unless emergency).
    
    Nigerian Clinic Rule: 
    - Standard: Payment must be cleared before dispensing
    - Emergency: Can override with proper authorization (flagged emergency)
    
    Args:
        value: Prescription instance
        emergency_override: Boolean flag for emergency override
    
    Returns:
        None if valid, raises ValidationError if invalid
    """
    if value is None:
        raise ValidationError(
            _("Prescription instance is required."),
            code='prescription_required',
        )
    
    # Emergency override - allow dispensing without payment
    if emergency_override:
        # Still validate that prescription exists and is in correct status
        if value.status != 'PENDING':
            raise ValidationError(
                _(
                    "Emergency dispensing can only be performed on PENDING prescriptions. "
                    "Current status: %(status)s"
                ) % {'status': value.status},
                code='invalid_status_emergency',
            )
        return  # Emergency override - skip payment check
    
    # Standard flow - payment must be cleared
    from apps.billing.billing_line_item_models import BillingLineItem
    
    # Find billing line item for this prescription's consultation
    billing_line_item = BillingLineItem.objects.filter(
        visit=value.visit,
        consultation=value.consultation,
        service_catalog__workflow_type='DRUG_DISPENSE',
    ).first()
    
    if not billing_line_item:
        raise ValidationError(
            _(
                "No billing found for this prescription. "
                "Please ensure billing has been generated for the pharmacy service."
            ),
            code='billing_not_found',
        )
    
    if billing_line_item.bill_status != 'PAID':
        raise ValidationError(
            _(
                "Prescription cannot be dispensed until billing is paid. "
                "Current billing status: %(status)s. "
                "Outstanding amount: ₦%(amount)s. "
                "Please process payment before dispensing. "
                "For emergency cases, use the emergency override flag."
            ) % {
                'status': billing_line_item.bill_status,
                'amount': billing_line_item.outstanding_amount,
            },
            code='payment_required',
        )
    
    # Validate prescription status
    if value.status != 'PENDING':
        raise ValidationError(
            _(
                "Only PENDING prescriptions can be dispensed. "
                "Current status: %(status)s"
            ) % {'status': value.status},
            code='invalid_status',
        )


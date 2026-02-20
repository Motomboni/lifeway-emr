"""
Payment Gates Service - Enforces pre-service payment rules.

Strict payment rules:
1. Registration must be paid before access to consultation.
2. Consultation must be paid before doctor can start encounter.
3. All other services (Lab, Pharmacy, Radiology, etc.) are post-consultation;
   payment is collected by Reception only; doctors/lab/pharmacy can add charges but not collect payment.

Insurance exception:
- Visits with approved insurance and payment_status in (SETTLED, INSURANCE_CLAIMED) are
  treated as having satisfied registration and consultation gates.
"""
from django.db.models import Q

from apps.visits.models import Visit
from .billing_line_item_models import BillingLineItem
from .service_catalog_models import ServiceCatalog


def _registration_line_items(queryset):
    """Filter queryset to Registration services only."""
    return queryset.filter(
        Q(service_catalog__service_code__istartswith='REG-') |
        Q(source_service_name__icontains='REGISTRATION') |
        Q(service_catalog__name__icontains='REGISTRATION')
    )


def _consultation_line_items(queryset):
    """Filter queryset to Consultation services only (exclude Registration)."""
    return queryset.filter(
        Q(service_catalog__service_code__istartswith='CONS-') |
        Q(service_catalog__department='CONSULTATION', service_catalog__workflow_type='GOPD_CONSULT') |
        Q(source_service_name__icontains='CONSULTATION') |
        Q(service_catalog__name__icontains='CONSULTATION')
    ).exclude(
        Q(service_catalog__service_code__istartswith='REG-') |
        Q(source_service_name__icontains='REGISTRATION') |
        Q(service_catalog__name__icontains='REGISTRATION')
    )


def _is_insurance_cleared(visit: Visit) -> bool:
    """
    Return True if visit has approved insurance and is settled/claimed.
    In this case, registration and consultation gates are satisfied by insurance.
    """
    if visit.payment_status in ('SETTLED', 'INSURANCE_CLAIMED'):
        return True
    # Fallback: check if insurance is approved even if visit status not yet synced
    if visit.payment_status == 'INSURANCE_PENDING':
        try:
            from .insurance_models import VisitInsurance
            if VisitInsurance.objects.filter(visit_id=visit.pk, approval_status='APPROVED').exists():
                return True
        except Exception:
            pass
    return False


def is_registration_paid(visit: Visit) -> bool:
    """
    True if the visit has at least one PAID billing line item for a Registration service,
    OR if the visit is fully covered by approved insurance.
    Registration services: service_code REG-*, name/description contains REGISTRATION.
    Also accepts amount_paid >= amount as paid (fallback when bill_status is inconsistent).
    Fallback: when visit payment_status indicates payment received (PAID/PARTIALLY_PAID/SETTLED)
    or when total paid >= charges, treat registration as satisfied.
    """
    # Insurance-covered visits satisfy registration gate
    if _is_insurance_cleared(visit):
        return True

    # Fallback: visit already shows payment received - gates are satisfied
    if visit.payment_status in ('PAID', 'SETTLED', 'PARTIALLY_PAID', 'INSURANCE_CLAIMED'):
        return True

    base = BillingLineItem.objects.filter(visit=visit).select_related('service_catalog')
    reg_items = _registration_line_items(base)
    # Check bill_status='PAID' first
    if reg_items.filter(bill_status='PAID').exists():
        return True
    # Fallback: amount_paid >= amount indicates fully paid (handles allocation edge cases)
    for item in reg_items:
        if item.amount_paid is not None and item.amount is not None:
            if item.amount_paid >= item.amount:
                return True

    # Fallback: outstanding_balance <= 0 (payment collected but allocation incomplete)
    try:
        from .billing_service import BillingService
        summary = BillingService.compute_billing_summary(visit)
        if summary.outstanding_balance <= 0:
            return True
    except Exception:
        pass
    return False


def is_consultation_paid(visit: Visit) -> bool:
    """
    True if the visit has at least one PAID billing line item for a Consultation service,
    OR if the visit is fully covered by approved insurance.
    Also accepts amount_paid >= amount as paid (fallback when bill_status is inconsistent).
    Fallback: when visit payment_status indicates payment received or outstanding_balance <= 0.
    """
    # Insurance-covered visits satisfy consultation gate
    if _is_insurance_cleared(visit):
        return True

    # Fallback: visit already shows payment received - gates are satisfied
    if visit.payment_status in ('PAID', 'SETTLED', 'PARTIALLY_PAID', 'INSURANCE_CLAIMED'):
        return True

    base = BillingLineItem.objects.filter(visit=visit).select_related('service_catalog')
    cons_items = _consultation_line_items(base)
    # Check bill_status='PAID' first
    if cons_items.filter(bill_status='PAID').exists():
        return True
    # Fallback: amount_paid >= amount indicates fully paid
    for item in cons_items:
        if item.amount_paid is not None and item.amount is not None:
            if item.amount_paid >= item.amount:
                return True

    # Fallback: outstanding_balance <= 0 (payment collected but allocation incomplete)
    try:
        from .billing_service import BillingService
        summary = BillingService.compute_billing_summary(visit)
        if summary.outstanding_balance <= 0:
            return True
    except Exception:
        pass
    return False


def get_payment_gates_status(visit: Visit) -> dict:
    """
    Return payment gates status for a visit (for API and UI).
    
    Returns:
        dict with:
        - registration_paid: bool
        - consultation_paid: bool
        - can_access_consultation: bool (registration_paid)
        - can_doctor_start_encounter: bool (consultation_paid)
    """
    reg_paid = is_registration_paid(visit)
    cons_paid = is_consultation_paid(visit)
    return {
        'registration_paid': reg_paid,
        'consultation_paid': cons_paid,
        'can_access_consultation': reg_paid,
        'can_doctor_start_encounter': cons_paid,
    }


def set_restricted_flags_on_catalog() -> None:
    """
    One-time: set restricted_service_flag=True for Registration and Consultation services.
    Call from data migration or management command.
    """
    # Registration: REG-* or name contains REGISTRATION
    ServiceCatalog.objects.filter(
        Q(service_code__istartswith='REG-') |
        Q(name__icontains='REGISTRATION')
    ).update(restricted_service_flag=True)
    
    # Consultation: CONS-* or department=CONSULTATION or name contains CONSULTATION (not registration)
    ServiceCatalog.objects.filter(
        Q(service_code__istartswith='CONS-') |
        Q(department='CONSULTATION', workflow_type='GOPD_CONSULT') |
        Q(name__icontains='CONSULTATION')
    ).exclude(
        Q(service_code__istartswith='REG-') | Q(name__icontains='REGISTRATION')
    ).update(restricted_service_flag=True)

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
    """
    # Insurance-covered visits satisfy registration gate
    if _is_insurance_cleared(visit):
        return True

    paid_registration = BillingLineItem.objects.filter(
        visit=visit,
        bill_status='PAID',
        service_catalog__restricted_service_flag=True,
    ).filter(
        Q(service_catalog__service_code__istartswith='REG-') |
        Q(source_service_name__icontains='REGISTRATION') |
        Q(service_catalog__name__icontains='REGISTRATION')
    ).exists()
    return paid_registration


def is_consultation_paid(visit: Visit) -> bool:
    """
    True if the visit has at least one PAID billing line item for a Consultation service,
    OR if the visit is fully covered by approved insurance.
    
    Matches consultation services by ANY of:
    - service_code starts with 'CONS-'
    - department='CONSULTATION' AND workflow_type='GOPD_CONSULT'
    - source_service_name contains 'CONSULTATION' (but not 'REGISTRATION')
    - service_catalog.name contains 'CONSULTATION' (but not 'REGISTRATION')
    
    Excludes registration services.
    """
    # Insurance-covered visits satisfy consultation gate
    if _is_insurance_cleared(visit):
        return True

    paid_consultation = BillingLineItem.objects.filter(
        visit=visit,
        bill_status='PAID',
    ).filter(
        Q(service_catalog__service_code__istartswith='CONS-') |
        Q(service_catalog__department='CONSULTATION', service_catalog__workflow_type='GOPD_CONSULT') |
        Q(source_service_name__icontains='CONSULTATION') |
        Q(service_catalog__name__icontains='CONSULTATION')
    ).exclude(
        Q(service_catalog__service_code__istartswith='REG-') |
        Q(source_service_name__icontains='REGISTRATION') |
        Q(service_catalog__name__icontains='REGISTRATION')
    ).exists()
    return paid_consultation


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

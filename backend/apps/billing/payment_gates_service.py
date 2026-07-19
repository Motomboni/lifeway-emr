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

from decimal import Decimal

from django.db.models import Q

from apps.visits.models import Visit

from .billing_line_item_models import BillingLineItem
from .service_catalog_models import ServiceCatalog


def _total_cleared_payments(visit: Visit) -> Decimal:
    """Sum CLEARED payments and completed wallet debits for gate allocation."""
    from .billing_service import BillingService

    return BillingService._compute_total_payments(
        visit
    ) + BillingService._compute_total_wallet_debits(visit)


def _registration_line_items(queryset):
    """Filter queryset to Registration services only."""
    return queryset.filter(
        Q(service_catalog__service_code__istartswith="REG-")
        | Q(source_service_name__icontains="REGISTRATION")
        | Q(service_catalog__name__icontains="REGISTRATION")
    )


def _consultation_line_items(queryset):
    """Filter queryset to Consultation services only (exclude Registration)."""
    return queryset.filter(
        Q(service_catalog__service_code__istartswith="CONS-")
        | Q(
            service_catalog__department="CONSULTATION",
            service_catalog__workflow_type="GOPD_CONSULT",
        )
        | Q(source_service_name__icontains="CONSULTATION")
        | Q(service_catalog__name__icontains="CONSULTATION")
    ).exclude(
        Q(service_catalog__service_code__istartswith="REG-")
        | Q(source_service_name__icontains="REGISTRATION")
        | Q(service_catalog__name__icontains="REGISTRATION")
    )


def _registration_visit_charges(visit: Visit):
    """Legacy VisitCharge rows that represent registration fees."""
    from .models import VisitCharge

    return VisitCharge.objects.filter(visit=visit).filter(
        Q(category="REGISTRATION")
        | Q(description__icontains="REGISTRATION")
    )


def _consultation_visit_charges(visit: Visit):
    """Legacy VisitCharge rows that represent consultation fees."""
    from .models import VisitCharge

    return VisitCharge.objects.filter(visit=visit).filter(
        Q(category="CONSULTATION") | Q(description__icontains="CONSULTATION")
    ).exclude(description__icontains="REGISTRATION")


def _sum_amounts(items) -> Decimal:
    total = Decimal("0.00")
    for item in items:
        total += item.amount or Decimal("0.00")
    return total


def _total_registration_due(visit: Visit) -> Decimal:
    base = BillingLineItem.objects.filter(visit=visit).select_related("service_catalog")
    line_total = _sum_amounts(_registration_line_items(base))
    charge_total = _sum_amounts(_registration_visit_charges(visit))
    return line_total + charge_total


def _total_consultation_due(visit: Visit) -> Decimal:
    base = BillingLineItem.objects.filter(visit=visit).select_related("service_catalog")
    line_total = _sum_amounts(_consultation_line_items(base))
    charge_total = _sum_amounts(_consultation_visit_charges(visit))
    return line_total + charge_total


def _is_insurance_cleared(visit: Visit) -> bool:
    """
    Return True if visit has approved insurance and is settled/claimed.
    In this case, registration and consultation gates are satisfied by insurance.
    """
    if visit.payment_status in ("SETTLED", "INSURANCE_CLAIMED"):
        return True
    if visit.payment_status == "INSURANCE_PENDING":
        try:
            from .insurance_models import VisitInsurance

            if VisitInsurance.objects.filter(
                visit_id=visit.pk, approval_status="APPROVED"
            ).exists():
                return True
        except Exception:
            pass
    return False


def _line_items_fully_paid(items) -> bool:
    """
    True only when every line item in the category is fully paid.
    Empty category => not paid (fee not yet collected).
    """
    if not items:
        return False
    for item in items:
        if item.bill_status == "PAID":
            continue
        if (
            item.amount_paid is not None
            and item.amount is not None
            and item.amount_paid >= item.amount
        ):
            continue
        return False
    return True


def is_registration_paid(visit: Visit) -> bool:
    """
    True when registration billing line items exist and are fully paid,
    or when cleared payments cover registration charges (including legacy VisitCharge),
    or when approved insurance covers the visit.
    """
    if _is_insurance_cleared(visit):
        return True

    base = BillingLineItem.objects.filter(visit=visit).select_related("service_catalog")
    reg_items = list(_registration_line_items(base))
    if reg_items and _line_items_fully_paid(reg_items):
        return True

    reg_due = _total_registration_due(visit)
    if reg_due <= 0:
        return False

    return _total_cleared_payments(visit) >= reg_due


def is_consultation_paid(visit: Visit) -> bool:
    """
    True when consultation billing line items exist and are fully paid,
    or when cleared payments cover registration + consultation charges,
    or when approved insurance covers the visit.
    """
    if _is_insurance_cleared(visit):
        return True

    base = BillingLineItem.objects.filter(visit=visit).select_related("service_catalog")
    cons_items = list(_consultation_line_items(base))
    if cons_items and _line_items_fully_paid(cons_items):
        return True

    cons_due = _total_consultation_due(visit)
    if cons_due <= 0:
        return False

    reg_due = _total_registration_due(visit)
    return _total_cleared_payments(visit) >= reg_due + cons_due


def is_clinical_access_allowed(visit: Visit) -> bool:
    """
    True when clinical modules may be used without full visit payment cleared.

    Per Lifeway strict rules: only registration must be paid upfront; lab, radiology,
    pharmacy, and consultation proceed while post-consultation charges remain pending.
    """
    return is_registration_paid(visit)


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
        "registration_paid": reg_paid,
        "consultation_paid": cons_paid,
        "can_access_consultation": reg_paid,
        "can_doctor_start_encounter": cons_paid,
    }


def set_restricted_flags_on_catalog() -> None:
    """
    One-time: set restricted_service_flag=True for Registration and Consultation services.
    Call from data migration or management command.
    """
    ServiceCatalog.objects.filter(
        Q(service_code__istartswith="REG-") | Q(name__icontains="REGISTRATION")
    ).update(restricted_service_flag=True)

    ServiceCatalog.objects.filter(
        Q(service_code__istartswith="CONS-")
        | Q(department="CONSULTATION", workflow_type="GOPD_CONSULT")
        | Q(name__icontains="CONSULTATION")
    ).exclude(
        Q(service_code__istartswith="REG-") | Q(name__icontains="REGISTRATION")
    ).update(restricted_service_flag=True)

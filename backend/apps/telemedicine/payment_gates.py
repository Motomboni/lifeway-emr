"""
Telemedicine payment gate enforcement.

Uses the shared billing payment_gates_service rules:
- Registration must be paid before any telemedicine access.
- Consultation must be paid before the doctor starts or joins a live encounter.
"""

from rest_framework.exceptions import PermissionDenied

from apps.billing.payment_gates_service import (
    is_clinical_access_allowed,
    is_consultation_paid,
)
from apps.visits.models import Visit


def _user_role(user) -> str | None:
    role = getattr(user, "role", None)
    if not role:
        role = getattr(user, "get_role", lambda: None)()
    return role


def enforce_telemedicine_payment_gates(
    visit: Visit,
    user,
    *,
    for_create: bool = False,
    for_doctor_encounter: bool = False,
) -> None:
    """
    Raise PermissionDenied when visit payment gates block telemedicine.

    for_create: session creation (doctor) — registration paid only.
    for_doctor_encounter: join/token/start for doctor — registration + consultation paid.
    Patient join/token: registration paid only.
    """
    try:
        visit.refresh_from_db()
    except Exception:
        pass

    if not is_clinical_access_allowed(visit):
        raise PermissionDenied(
            detail=(
                "Registration payment is required before telemedicine. "
                "Please collect registration payment at reception."
            ),
            code="registration_payment_required",
        )

    if for_create:
        return

    role = _user_role(user)
    if for_doctor_encounter or role == "DOCTOR":
        if not is_consultation_paid(visit):
            raise PermissionDenied(
                detail=(
                    "Consultation payment is required before starting telemedicine. "
                    "Please collect consultation payment at reception."
                ),
                code="consultation_payment_required",
            )

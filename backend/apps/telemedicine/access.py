"""
Telemedicine session access helpers for the virtual clinic.

Supports doctor host, patient, and invited clinical staff (nurse, etc.).
"""

from __future__ import annotations

INVITABLE_STAFF_ROLES = (
    "NURSE",
    "DOCTOR",
    "LAB_TECH",
    "RADIOLOGY_TECH",
    "PHARMACIST",
    "ADMIN",
    "IVF_SPECIALIST",
    "EMBRYOLOGIST",
)

CLINIC_ROLE_CHOICES = [
    ("HOST", "Host doctor"),
    ("PATIENT", "Patient"),
    ("NURSE", "Nurse"),
    ("SPECIALIST", "Specialist"),
    ("OBSERVER", "Observer"),
    ("STAFF", "Clinical staff"),
]

INVITE_STATUS_CHOICES = [
    ("PENDING", "Pending"),
    ("ACCEPTED", "Accepted"),
    ("DECLINED", "Declined"),
    ("REVOKED", "Revoked"),
]

ACTIVE_INVITE_STATUSES = ("PENDING", "ACCEPTED")

# Virtual clinic rooms support doctor + patient + invited staff
VIRTUAL_CLINIC_MAX_PARTICIPANTS = 8


def user_role(user) -> str | None:
    role = getattr(user, "role", None)
    if not role:
        role = getattr(user, "get_role", lambda: None)()
    return role


def default_clinic_role_for_user(user) -> str:
    role = user_role(user)
    if role == "DOCTOR":
        return "SPECIALIST"
    if role == "NURSE":
        return "NURSE"
    if role in ("LAB_TECH", "RADIOLOGY_TECH", "PHARMACIST", "EMBRYOLOGIST"):
        return "STAFF"
    if role == "IVF_SPECIALIST":
        return "SPECIALIST"
    return "OBSERVER"


def get_patient_for_user(user):
    from apps.patients.models import Patient

    try:
        return Patient.objects.get(user=user, is_active=True)
    except Patient.DoesNotExist:
        return None


def is_session_host(user, session) -> bool:
    return session.doctor_id == getattr(user, "id", None)


def is_session_patient(user, session) -> bool:
    if user_role(user) != "PATIENT":
        return False
    patient = get_patient_for_user(user)
    return bool(patient and session.patient_id == patient.id)


def get_active_invite(user, session):
    from .models import TelemedicineParticipant

    return (
        TelemedicineParticipant.objects.filter(
            session=session,
            user=user,
            invite_status__in=ACTIVE_INVITE_STATUSES,
        )
        .exclude(clinic_role__in=("HOST", "PATIENT"))
        .first()
    )


def user_can_view_session(user, session) -> bool:
    if is_session_host(user, session):
        return True
    if is_session_patient(user, session):
        return True
    return get_active_invite(user, session) is not None


def user_can_join_session(user, session) -> bool:
    if session.status in ("COMPLETED", "CANCELLED", "FAILED"):
        return False
    return user_can_view_session(user, session)


def user_can_invite_staff(user, session) -> bool:
    role = user_role(user)
    if role == "DOCTOR" and is_session_host(user, session):
        return True
    if role == "ADMIN":
        return True
    return False

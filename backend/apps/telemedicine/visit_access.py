"""Telemedicine visit access checks — org scope and doctor assignment."""

from rest_framework.exceptions import PermissionDenied

from core.tenant import assert_visit_in_organization


def assert_telemedicine_visit_access(visit, doctor, request) -> None:
    """Ensure visit belongs to tenant and doctor may manage telemedicine for it."""
    assert_visit_in_organization(visit, request)

    if getattr(visit, "appointment_id", None) and visit.appointment:
        if visit.appointment.doctor_id != doctor.id:
            raise PermissionDenied(
                "You are not the assigned doctor for this visit's appointment."
            )
        return

    from apps.appointments.models import Appointment

    linked = (
        Appointment.objects.filter(
            visit=visit,
            status__in=("SCHEDULED", "CONFIRMED", "COMPLETED"),
        )
        .order_by("-appointment_date")
        .first()
    )
    if linked and linked.doctor_id != doctor.id:
        raise PermissionDenied(
            "You are not the assigned doctor for this visit."
        )

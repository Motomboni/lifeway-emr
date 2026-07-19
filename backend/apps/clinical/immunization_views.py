"""Nigeria EPI immunization schedule API."""

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from core.tenant import assert_patient_in_organization, get_org_scoped_patient

from .immunization_models import ImmunizationRecord


class CanManageImmunizations(BasePermission):
    """Doctors, nurses, and administrators may manage immunization records."""

    allowed_roles = {"DOCTOR", "NURSE", "ADMIN"}

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = getattr(request.user, "role", None) or getattr(
            request.user, "get_role", lambda: None
        )()
        return role in self.allowed_roles


def serialize_immunization_record(record: ImmunizationRecord) -> dict:
    return _serialize(record)


def _serialize(record: ImmunizationRecord) -> dict:
    return {
        "id": record.id,
        "patient_id": record.patient_id,
        "vaccine": record.vaccine,
        "dose_number": record.dose_number,
        "scheduled_date": record.scheduled_date,
        "administered_date": record.administered_date,
        "batch_number": record.batch_number,
        "administered_by": record.administered_by_id,
        "notes": record.notes,
        "created_at": record.created_at,
    }


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, CanManageImmunizations])
def patient_immunizations(request, patient_id: int):
    patient = get_org_scoped_patient(request, patient_id)
    if not patient.is_active:
        from django.http import Http404

        raise Http404("Patient not found.")
    if request.method == "GET":
        qs = ImmunizationRecord.objects.filter(patient=patient).select_related(
            "administered_by"
        )
        return Response([_serialize(r) for r in qs])

    record = ImmunizationRecord.objects.create(
        patient=patient,
        vaccine=request.data.get("vaccine", "BCG"),
        dose_number=int(request.data.get("dose_number") or 1),
        scheduled_date=request.data.get("scheduled_date") or None,
        administered_date=request.data.get("administered_date") or None,
        batch_number=request.data.get("batch_number") or "",
        administered_by=request.user if request.data.get("administered") else None,
        notes=request.data.get("notes") or "",
    )
    if request.data.get("administered") and not record.administered_date:
        record.administered_date = timezone.now().date()
        record.administered_by = request.user
        record.save(update_fields=["administered_date", "administered_by"])
    return Response(_serialize(record), status=status.HTTP_201_CREATED)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated, CanManageImmunizations])
def immunization_detail(request, record_id: int):
    from django.shortcuts import get_object_or_404

    record = get_object_or_404(
        ImmunizationRecord.objects.select_related("patient"), id=record_id
    )
    assert_patient_in_organization(record.patient, request)
    for field in (
        "vaccine",
        "dose_number",
        "scheduled_date",
        "administered_date",
        "batch_number",
        "notes",
    ):
        if field in request.data:
            setattr(record, field, request.data[field])
    if request.data.get("mark_administered"):
        # Preserve a supplied historical administration date; default to today.
        if "administered_date" not in request.data:
            record.administered_date = timezone.now().date()
        record.administered_by = request.user
    record.save()
    return Response(_serialize(record))

"""
Global AI endpoints (not visit-scoped): clinical note generation.

POST /api/v1/ai/generate-note — generate structured note (doctor approves before save).
POST /api/v1/ai/notes/ — save approved/edited clinical note.
"""
import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone

from core.permissions import IsDoctor
from core.audit import AuditLog
from .clinical_notes_service import generate_clinical_note
from .services import AIServiceError
from .serializers import (
    GenerateNoteRequestSerializer,
    GenerateNoteResponseSerializer,
    ClinicalNoteSerializer,
)
from .models import ClinicalNote

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsDoctor])
def generate_note(request):
    """
    POST /api/v1/ai/generate-note
    Body: { "transcript": "...", "note_type": "SOAP"|"summary"|"discharge", "appointment_id": optional }
    Returns structured note for doctor to edit/approve before save.
    """
    serializer = GenerateNoteRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    transcript = serializer.validated_data.get('transcript', '')
    note_type = serializer.validated_data.get('note_type', 'summary')
    appointment_id = serializer.validated_data.get('appointment_id')

    visit = None
    if appointment_id:
        from apps.appointments.models import Appointment
        appointment = get_object_or_404(Appointment, id=appointment_id)
        if appointment.doctor_id != request.user.id:
            raise PermissionDenied("You can only generate notes for your own appointments.")
        visit = appointment.visit

    try:
        result = generate_clinical_note(
            transcript=transcript,
            note_type=note_type,
            user=request.user,
            visit=visit,
        )
    except AIServiceError as e:
        return Response(
            {'detail': str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    AuditLog.log(
        user=request.user,
        role=getattr(request.user, 'role', 'DOCTOR'),
        action='AI_CLINICAL_NOTE_GENERATED',
        visit_id=visit.id if visit else None,
        resource_type='clinical_note',
        resource_id=None,
        request=request,
        metadata={'note_type': result['note_type']},
    )
    return Response(
        GenerateNoteResponseSerializer(result).data,
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsDoctor])
def save_clinical_note(request):
    """
    POST /api/v1/ai/notes/
    Body: patient_id, appointment_id (optional), note_type, raw_transcript, ai_generated_note, doctor_edited_note
    Save approved/edited clinical note.
    """
    from apps.patients.models import Patient
    from apps.appointments.models import Appointment
    patient_id = request.data.get('patient_id')
    if not patient_id:
        return Response(
            {'patient_id': ['This field is required.']},
            status=status.HTTP_400_BAD_REQUEST,
        )
    patient = get_object_or_404(Patient, id=patient_id, is_active=True)
    appointment_id = request.data.get('appointment_id')
    appointment = None
    if appointment_id:
        appointment = get_object_or_404(Appointment, id=appointment_id)
        if appointment.doctor_id != request.user.id:
            raise PermissionDenied("You can only save notes for your own appointments.")
    note_type = request.data.get('note_type', 'summary')
    raw_transcript = request.data.get('raw_transcript', '')
    ai_generated_note = request.data.get('ai_generated_note', '')
    doctor_edited_note = request.data.get('doctor_edited_note', '') or ai_generated_note
    note = ClinicalNote.objects.create(
        patient=patient,
        doctor=request.user,
        appointment=appointment,
        note_type=note_type,
        raw_transcript=raw_transcript,
        ai_generated_note=ai_generated_note,
        doctor_edited_note=doctor_edited_note,
        approved_at=timezone.now(),
    )
    AuditLog.log(
        user=request.user,
        role=getattr(request.user, 'role', 'DOCTOR'),
        action='CLINICAL_NOTE_APPROVED',
        visit_id=note.appointment.visit_id if note.appointment else None,
        resource_type='clinical_note',
        resource_id=note.id,
        request=request,
    )
    return Response(
        ClinicalNoteSerializer(note).data,
        status=status.HTTP_201_CREATED,
    )

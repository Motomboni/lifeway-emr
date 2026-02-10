"""National Health ID verification endpoint. Prevent duplicate IDs; log attempts."""
import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from django.utils import timezone

from apps.patients.models import Patient
from apps.patients.nhid_service import verify_national_health_id

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_nhid(request):
    """
    POST /api/v1/nhid/verify
    Body: { "id_number": "...", "name": "...", "dob": "YYYY-MM-DD", "patient_id": <id> }
    If valid: set patient.national_health_id and id_verified=True.
    Prevents duplicate IDs; logs verification attempts.
    """
    id_number = (request.data.get('id_number') or '').strip()
    name = (request.data.get('name') or '').strip()
    dob_raw = request.data.get('dob')
    patient_id = request.data.get('patient_id')
    if not patient_id:
        return Response(
            {'patient_id': ['This field is required.']},
            status=status.HTTP_400_BAD_REQUEST,
        )
    patient = get_object_or_404(Patient, id=patient_id, is_active=True)
    if not id_number:
        return Response(
            {'id_number': ['This field is required.']},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not name:
        return Response(
            {'name': ['This field is required.']},
            status=status.HTTP_400_BAD_REQUEST,
        )
    dob = None
    if dob_raw:
        dob = parse_date(dob_raw) if isinstance(dob_raw, str) else dob_raw
    if not dob:
        return Response(
            {'dob': ['Valid date of birth is required (YYYY-MM-DD).']},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if Patient.objects.filter(national_health_id=id_number).exclude(id=patient.id).exists():
        logger.warning("NHID duplicate attempt: id=%s patient_id=%s", id_number[:4] + "***", patient_id)
        return Response(
            {'detail': 'This National Health ID is already registered for another patient.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    valid, message = verify_national_health_id(id_number, name, dob)
    if not valid:
        return Response(
            {'detail': message},
            status=status.HTTP_400_BAD_REQUEST,
        )
    patient.national_health_id = id_number
    patient.id_verified = True
    patient.save(update_fields=['national_health_id', 'id_verified'])
    return Response({
        'detail': 'National Health ID verified and saved.',
        'patient_id': patient.id,
        'id_verified': True,
    }, status=status.HTTP_200_OK)

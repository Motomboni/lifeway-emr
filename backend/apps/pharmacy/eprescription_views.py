"""E-Prescription API: interaction check and create (doctor only)."""
import logging
from django.db import models
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404

from core.permissions import IsDoctor
from core.audit import AuditLog
from .models import Medication, EPrescription, EPrescriptionItem
from .drug_interaction_service import check_drug_interactions
from .eprescription_serializers import (
    MedicationSerializer,
    EPrescriptionSerializer,
    EPrescriptionCreateSerializer,
    CheckInteractionsSerializer,
)

logger = logging.getLogger(__name__)


class MedicationViewSet(viewsets.ReadOnlyModelViewSet):
    """List/search medications for e-prescription (doctor)."""
    serializer_class = MedicationSerializer
    permission_classes = [IsAuthenticated, IsDoctor]
    queryset = Medication.objects.filter(is_active=True).order_by('name')

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                models.Q(name__icontains=search) |
                models.Q(generic_name__icontains=search)
            )
        return qs

    @action(detail=False, methods=['post'], url_path='check-interactions')
    def check_interactions(self, request):
        """POST medication_ids -> list of interaction warnings (Mild/Moderate/Severe)."""
        serializer = CheckInteractionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        medication_ids = serializer.validated_data['medication_ids']
        warnings = check_drug_interactions(medication_ids)
        return Response({'warnings': warnings})

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                models.Q(name__icontains=search) | models.Q(generic_name__icontains=search)
            )
        return qs


class EPrescriptionViewSet(viewsets.ModelViewSet):
    """Create/list e-prescriptions. Doctor only. Interaction check before save."""
    serializer_class = EPrescriptionSerializer
    permission_classes = [IsAuthenticated, IsDoctor]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'role', None) == 'DOCTOR':
            return EPrescription.objects.filter(doctor=user).select_related('patient', 'doctor').prefetch_related('items__medication')
        return EPrescription.objects.none()

    def create(self, request, *args, **kwargs):
        serializer = EPrescriptionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        from apps.patients.models import Patient
        patient = get_object_or_404(Patient, id=data['patient_id'], is_active=True)
        medication_ids = [m['medication_id'] for m in data['medications']]
        warnings = check_drug_interactions(medication_ids)
        severe = [w for w in warnings if w['severity'] == 'Severe']
        if severe and not (data.get('override_reason') or '').strip():
            return Response(
                {
                    'detail': 'Severe drug interaction(s) detected. Provide override_reason to proceed.',
                    'warnings': warnings,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        ep = EPrescription.objects.create(
            patient=patient,
            doctor=request.user,
            notes=data.get('notes', ''),
            override_reason=data.get('override_reason', ''),
            status='active',
        )
        for m in data['medications']:
            med = get_object_or_404(Medication, id=m['medication_id'], is_active=True)
            EPrescriptionItem.objects.create(
                eprescription=ep,
                medication=med,
                dosage=m.get('dosage', ''),
                frequency=m.get('frequency', ''),
                duration=m.get('duration', ''),
            )
        AuditLog.log(
            user=request.user,
            role='DOCTOR',
            action='EPRESCRIPTION_CREATED',
            visit_id=None,
            resource_type='eprescription',
            resource_id=ep.id,
            request=request,
            metadata={'warnings_count': len(warnings), 'override': bool(data.get('override_reason'))},
        )
        return Response(
            EPrescriptionSerializer(ep).data,
            status=status.HTTP_201_CREATED,
        )
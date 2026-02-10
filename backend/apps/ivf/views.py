"""
IVF Module API Views

Comprehensive API endpoints for IVF treatment management.
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Count, Q

from .models import (
    IVFCycle, OvarianStimulation, OocyteRetrieval, SpermAnalysis,
    Embryo, EmbryoTransfer, IVFMedication, IVFOutcome, IVFConsent
)
from .serializers import (
    IVFCycleListSerializer, IVFCycleDetailSerializer,
    IVFCycleCreateSerializer, IVFCycleUpdateSerializer,
    IVFCycleFullSerializer, OvarianStimulationSerializer,
    OocyteRetrievalSerializer, SpermAnalysisListSerializer,
    SpermAnalysisDetailSerializer, EmbryoListSerializer,
    EmbryoDetailSerializer, EmbryoTransferSerializer,
    IVFMedicationSerializer, IVFOutcomeSerializer, IVFConsentSerializer,
    EmbryoInventorySerializer, IVFPatientListSerializer,
)
from .permissions import (
    IsIVFSpecialist, IsEmbryologist, CanViewIVFRecords,
    IVFConsentRequired, CanManageEmbryoDisposition,
    IsIVFNurse, CanRecordStimulationMonitoring, CanRecordMedicationAdministration
)


class IVFCycleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for IVF Cycle management.
    
    Provides CRUD operations and additional actions for cycle management.
    
    Permissions:
    - IVF_SPECIALIST/ADMIN: Full access (create, update, cancel cycles)
    - NURSE: Read access + can view for patient care
    - DOCTOR: Read-only access
    - EMBRYOLOGIST: Read access for lab coordination
    """
    
    queryset = IVFCycle.objects.select_related(
        'patient', 'partner', 'created_by'
    ).prefetch_related('embryos', 'medications', 'consents')
    
    permission_classes = [IsAuthenticated, IsIVFNurse]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'cycle_type', 'patient', 'consent_signed']
    search_fields = ['patient__first_name', 'patient__last_name', 'patient__mrn']
    ordering_fields = ['created_at', 'actual_start_date', 'cycle_number']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return IVFCycleListSerializer
        elif self.action == 'create':
            return IVFCycleCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return IVFCycleUpdateSerializer
        elif self.action == 'retrieve' or self.action == 'full_details':
            return IVFCycleFullSerializer
        return IVFCycleDetailSerializer
    
    def _check_write_permission(self):
        """Check if user has permission to create/modify cycles."""
        user_role = getattr(self.request.user, 'role', None)
        if user_role not in ['ADMIN', 'IVF_SPECIALIST']:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                detail="Only IVF Specialists can create or modify IVF cycles. "
                       "Nurses can view cycles and record monitoring data.",
                code='cycle_write_not_allowed'
            )
    
    def create(self, request, *args, **kwargs):
        """Create a new IVF cycle - IVF Specialist only."""
        self._check_write_permission()
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """Update an IVF cycle - IVF Specialist only."""
        self._check_write_permission()
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        """Partially update an IVF cycle - IVF Specialist only."""
        self._check_write_permission()
        return super().partial_update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Delete an IVF cycle - IVF Specialist only."""
        self._check_write_permission()
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['get'])
    def full_details(self, request, pk=None):
        """Get complete cycle details with all related data."""
        cycle = self.get_object()
        serializer = IVFCycleFullSerializer(cycle)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an IVF cycle - IVF Specialist only."""
        self._check_write_permission()
        cycle = self.get_object()
        
        reason = request.data.get('reason')
        notes = request.data.get('notes', '')
        
        if not reason:
            return Response(
                {'error': 'Cancellation reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            cycle.cancel(reason=reason, notes=notes, user=request.user)
            return Response({
                'message': 'Cycle cancelled successfully',
                'cycle_id': cycle.id,
                'status': cycle.status
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def sign_consent(self, request, pk=None):
        """Mark consent as signed - IVF Specialist only."""
        self._check_write_permission()
        cycle = self.get_object()
        
        consent_type = request.data.get('consent_type', 'patient')
        
        if consent_type == 'patient':
            cycle.consent_signed = True
            cycle.consent_date = timezone.now().date()
        elif consent_type == 'partner':
            cycle.partner_consent_signed = True
            cycle.partner_consent_date = timezone.now().date()
        else:
            return Response(
                {'error': 'Invalid consent type'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cycle.save()
        
        return Response({
            'message': f'{consent_type.title()} consent signed successfully',
            'consent_signed': cycle.consent_signed,
            'partner_consent_signed': cycle.partner_consent_signed
        })
    
    @action(detail=True, methods=['post'])
    def advance_status(self, request, pk=None):
        """Advance cycle to next status - IVF Specialist only."""
        self._check_write_permission()
        cycle = self.get_object()
        
        new_status = request.data.get('status')
        
        if not new_status:
            return Response(
                {'error': 'New status is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate status transition
        valid_statuses = [choice[0] for choice in IVFCycle.Status.choices]
        if new_status not in valid_statuses:
            return Response(
                {'error': f'Invalid status. Valid options: {valid_statuses}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            cycle.status = new_status
            cycle.save()
            return Response({
                'message': 'Cycle status updated',
                'new_status': cycle.status
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get IVF statistics dashboard data."""
        # Date range filter
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        queryset = self.get_queryset()
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        # Calculate statistics
        total_cycles = queryset.count()
        
        cycles_by_status = queryset.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        cycles_by_type = queryset.values('cycle_type').annotate(
            count=Count('id')
        ).order_by('cycle_type')
        
        # Pregnancy rates
        completed_cycles = queryset.exclude(
            status__in=['PLANNED', 'STIMULATION', 'RETRIEVAL', 'CANCELLED']
        )
        
        pregnancies = completed_cycles.filter(
            pregnancy_outcome__in=['POSITIVE', 'ONGOING', 'LIVE_BIRTH']
        ).count()
        
        clinical_pregnancies = completed_cycles.filter(
            outcome__clinical_pregnancy=True
        ).count()
        
        live_births = completed_cycles.filter(
            pregnancy_outcome='LIVE_BIRTH'
        ).count()
        
        completed_count = completed_cycles.count()
        
        return Response({
            'total_cycles': total_cycles,
            'cycles_by_status': list(cycles_by_status),
            'cycles_by_type': list(cycles_by_type),
            'pregnancy_rate': (pregnancies / completed_count * 100) if completed_count > 0 else 0,
            'clinical_pregnancy_rate': (clinical_pregnancies / completed_count * 100) if completed_count > 0 else 0,
            'live_birth_rate': (live_births / completed_count * 100) if completed_count > 0 else 0,
            'completed_cycles': completed_count
        })


class OvarianStimulationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ovarian stimulation monitoring.
    
    Nurses play a key role here - they record daily monitoring data
    including hormone levels, follicle measurements, and vitals.
    """
    
    serializer_class = OvarianStimulationSerializer
    permission_classes = [IsAuthenticated, CanRecordStimulationMonitoring]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['cycle', 'date']
    ordering = ['cycle', 'day']
    
    def get_queryset(self):
        return OvarianStimulation.objects.select_related(
            'cycle', 'recorded_by'
        ).filter(cycle_id=self.kwargs.get('cycle_pk'))
    
    def perform_create(self, serializer):
        serializer.save(
            cycle_id=self.kwargs.get('cycle_pk'),
            recorded_by=self.request.user
        )


class OocyteRetrievalViewSet(viewsets.ModelViewSet):
    """ViewSet for oocyte retrieval procedures."""
    
    serializer_class = OocyteRetrievalSerializer
    permission_classes = [IsAuthenticated, IsIVFSpecialist]
    
    def get_queryset(self):
        return OocyteRetrieval.objects.select_related(
            'cycle', 'performed_by'
        ).filter(cycle_id=self.kwargs.get('cycle_pk'))
    
    def perform_create(self, serializer):
        serializer.save(
            cycle_id=self.kwargs.get('cycle_pk'),
            performed_by=self.request.user
        )


class SpermAnalysisViewSet(viewsets.ModelViewSet):
    """ViewSet for sperm analysis records."""
    
    permission_classes = [IsAuthenticated, IsEmbryologist]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['patient', 'cycle', 'sample_source', 'assessment']
    search_fields = ['patient__first_name', 'patient__last_name']
    ordering = ['-collection_date']
    
    def get_queryset(self):
        return SpermAnalysis.objects.select_related(
            'patient', 'cycle', 'analyzed_by'
        )
    
    def get_serializer_class(self):
        if self.action == 'list':
            return SpermAnalysisListSerializer
        return SpermAnalysisDetailSerializer


class EmbryoViewSet(viewsets.ModelViewSet):
    """ViewSet for embryo management."""
    
    permission_classes = [IsAuthenticated, IsEmbryologist, IVFConsentRequired]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['cycle', 'status', 'fertilization_method', 'pgt_performed', 'pgt_result']
    ordering = ['cycle', 'embryo_number']
    
    def get_queryset(self):
        cycle_pk = self.kwargs.get('cycle_pk')
        queryset = Embryo.objects.select_related('cycle', 'created_by')
        
        if cycle_pk:
            queryset = queryset.filter(cycle_id=cycle_pk)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return EmbryoListSerializer
        return EmbryoDetailSerializer
    
    def perform_create(self, serializer):
        cycle_pk = self.kwargs.get('cycle_pk')
        serializer.save(
            cycle_id=cycle_pk,
            created_by=self.request.user
        )
    
    @action(detail=True, methods=['post'])
    def freeze(self, request, pk=None, **kwargs):
        """Freeze an embryo."""
        embryo = self.get_object()
        
        storage_location = request.data.get('storage_location')
        straw_id = request.data.get('straw_id')
        
        if not storage_location:
            return Response(
                {'error': 'Storage location is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        embryo.status = Embryo.Status.FROZEN
        embryo.frozen_date = timezone.now().date()
        embryo.storage_location = storage_location
        embryo.straw_id = straw_id or ''
        embryo.save()
        
        return Response({
            'message': 'Embryo frozen successfully',
            'lab_id': embryo.lab_id,
            'storage_location': embryo.storage_location
        })
    
    @action(detail=True, methods=['post'])
    def thaw(self, request, pk=None, **kwargs):
        """Thaw a frozen embryo."""
        embryo = self.get_object()
        
        if embryo.status != Embryo.Status.FROZEN:
            return Response(
                {'error': 'Only frozen embryos can be thawed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        survived = request.data.get('survived', True)
        
        embryo.status = Embryo.Status.THAWED
        embryo.thaw_date = timezone.now().date()
        embryo.survived_thaw = survived
        embryo.save()
        
        return Response({
            'message': 'Embryo thawed',
            'lab_id': embryo.lab_id,
            'survived': embryo.survived_thaw
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CanManageEmbryoDisposition])
    def dispose(self, request, pk=None, **kwargs):
        """Set embryo disposition."""
        embryo = self.get_object()
        
        disposition = request.data.get('disposition')
        notes = request.data.get('notes', '')
        
        if not disposition:
            return Response(
                {'error': 'Disposition type is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        embryo.disposition = disposition
        embryo.disposition_date = timezone.now().date()
        embryo.disposition_notes = notes
        
        if disposition in ['DISCARDED_QUALITY', 'DISCARDED_CONSENT', 'DISCARDED_EXPIRED']:
            embryo.status = Embryo.Status.DISCARDED
        elif disposition == 'DONATED_RESEARCH' or disposition == 'DONATED_PATIENT':
            embryo.status = Embryo.Status.DONATED
        
        embryo.save()
        
        return Response({
            'message': 'Embryo disposition recorded',
            'lab_id': embryo.lab_id,
            'disposition': embryo.disposition
        })


class EmbryoTransferViewSet(viewsets.ModelViewSet):
    """ViewSet for embryo transfer procedures."""
    
    serializer_class = EmbryoTransferSerializer
    permission_classes = [IsAuthenticated, IsIVFSpecialist, IVFConsentRequired]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['cycle', 'transfer_type']
    ordering = ['-transfer_date']
    
    def get_queryset(self):
        cycle_pk = self.kwargs.get('cycle_pk')
        queryset = EmbryoTransfer.objects.select_related(
            'cycle', 'performed_by'
        ).prefetch_related('embryos')
        
        if cycle_pk:
            queryset = queryset.filter(cycle_id=cycle_pk)
        
        return queryset
    
    def perform_create(self, serializer):
        cycle_pk = self.kwargs.get('cycle_pk')
        transfer = serializer.save(
            cycle_id=cycle_pk,
            performed_by=self.request.user
        )
        
        # Update transferred embryos status
        transfer.embryos.update(status=Embryo.Status.TRANSFERRED)


class IVFMedicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for IVF medication management.
    
    - IVF Specialist: Can prescribe and manage medications
    - Nurse: Can view medications and record administration
    """
    
    serializer_class = IVFMedicationSerializer
    permission_classes = [IsAuthenticated, CanRecordMedicationAdministration]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['cycle', 'category']
    ordering = ['start_date']
    
    def get_queryset(self):
        cycle_pk = self.kwargs.get('cycle_pk')
        queryset = IVFMedication.objects.select_related('cycle', 'prescribed_by')
        
        if cycle_pk:
            queryset = queryset.filter(cycle_id=cycle_pk)
        
        return queryset
    
    def perform_create(self, serializer):
        # Only IVF_SPECIALIST and ADMIN can prescribe new medications
        user_role = getattr(self.request.user, 'role', None)
        if user_role not in ['ADMIN', 'IVF_SPECIALIST']:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                detail="Only IVF Specialists can prescribe medications. "
                       "Nurses can record administration of existing prescriptions.",
                code='prescribe_not_allowed'
            )
        
        cycle_pk = self.kwargs.get('cycle_pk')
        serializer.save(
            cycle_id=cycle_pk,
            prescribed_by=self.request.user
        )


class IVFOutcomeViewSet(viewsets.ModelViewSet):
    """ViewSet for IVF outcome tracking."""
    
    serializer_class = IVFOutcomeSerializer
    permission_classes = [IsAuthenticated, IsIVFSpecialist]
    
    def get_queryset(self):
        return IVFOutcome.objects.select_related('cycle', 'recorded_by')
    
    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)


class IVFConsentViewSet(viewsets.ModelViewSet):
    """ViewSet for IVF consent management."""
    
    serializer_class = IVFConsentSerializer
    permission_classes = [IsAuthenticated, IsIVFSpecialist]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['cycle', 'consent_type', 'signed', 'revoked']
    ordering = ['-created_at']
    
    def get_queryset(self):
        cycle_pk = self.kwargs.get('cycle_pk')
        queryset = IVFConsent.objects.select_related('cycle', 'patient', 'recorded_by')
        
        if cycle_pk:
            queryset = queryset.filter(cycle_id=cycle_pk)
        
        return queryset
    
    def perform_create(self, serializer):
        cycle_pk = self.kwargs.get('cycle_pk')
        serializer.save(
            cycle_id=cycle_pk,
            recorded_by=self.request.user
        )
    
    @action(detail=True, methods=['post'])
    def sign(self, request, pk=None, **kwargs):
        """Sign a consent form."""
        consent = self.get_object()
        
        witness_name = request.data.get('witness_name', '')
        
        consent.signed = True
        consent.signed_date = timezone.now().date()
        consent.signed_time = timezone.now().time()
        consent.witness_name = witness_name
        consent.witness_signature = bool(witness_name)
        consent.save()
        
        # Update cycle consent status if this is treatment consent
        if consent.consent_type == IVFConsent.ConsentType.TREATMENT:
            cycle = consent.cycle
            if consent.patient == cycle.patient:
                cycle.consent_signed = True
                cycle.consent_date = consent.signed_date
            elif consent.patient == cycle.partner:
                cycle.partner_consent_signed = True
                cycle.partner_consent_date = consent.signed_date
            cycle.save()
        
        return Response({
            'message': 'Consent signed successfully',
            'consent_id': consent.id,
            'consent_type': consent.consent_type
        })
    
    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None, **kwargs):
        """Revoke a consent."""
        consent = self.get_object()
        
        reason = request.data.get('reason', '')
        
        if not reason:
            return Response(
                {'error': 'Revocation reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        consent.revoked = True
        consent.revoked_date = timezone.now().date()
        consent.revocation_reason = reason
        consent.save()
        
        return Response({
            'message': 'Consent revoked',
            'consent_id': consent.id
        })


class EmbryoInventoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing embryo inventory (primarily frozen embryos).
    
    Provides a centralized view of all embryos across cycles with
    filtering by status, grade, and patient.
    """
    
    permission_classes = [IsAuthenticated, CanViewIVFRecords]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'pgt_result']
    search_fields = ['cycle__patient__first_name', 'cycle__patient__last_name', 'lab_id']
    ordering = ['-frozen_date', '-created_at']
    
    def get_queryset(self):
        queryset = Embryo.objects.select_related(
            'cycle', 'cycle__patient', 'cycle__partner', 'created_by'
        )
        
        # Filter by grade if provided
        grade = self.request.query_params.get('grade')
        if grade:
            queryset = queryset.filter(
                Q(blastocyst_grade__icontains=grade) | Q(day3_grade__icontains=grade)
            )
        
        # Filter by patient if provided
        patient = self.request.query_params.get('patient')
        if patient:
            queryset = queryset.filter(cycle__patient_id=patient)
        
        return queryset
    
    def get_serializer_class(self):
        return EmbryoInventorySerializer
    
    @action(detail=True, methods=['post'])
    def thaw(self, request, pk=None):
        """Thaw an embryo from inventory."""
        embryo = self.get_object()
        
        if embryo.status != Embryo.Status.FROZEN:
            return Response(
                {'error': 'Only frozen embryos can be thawed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        thaw_date = request.data.get('thaw_date', timezone.now().date())
        notes = request.data.get('notes', '')
        
        embryo.status = Embryo.Status.THAWED
        embryo.thaw_date = thaw_date
        embryo.notes = (embryo.notes or '') + f'\nThaw notes: {notes}'
        embryo.survived_thaw = True
        embryo.save()
        
        return Response({
            'message': 'Embryo thawed successfully',
            'embryo_id': embryo.id
        })
    
    @action(detail=True, methods=['post'])
    def dispose(self, request, pk=None):
        """Dispose an embryo from inventory."""
        embryo = self.get_object()
        
        reason = request.data.get('reason')
        notes = request.data.get('notes', '')
        
        if not reason:
            return Response(
                {'error': 'Disposal reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        embryo.status = Embryo.Status.DISCARDED
        embryo.disposition = reason
        embryo.disposition_date = timezone.now().date()
        embryo.disposition_notes = notes
        embryo.save()
        
        return Response({
            'message': 'Embryo disposed successfully',
            'embryo_id': embryo.id
        })


class IVFPatientsListView(APIView):
    """
    List patients who have at least one IVF cycle (IVF patients only).
    Used by the IVF dashboard for "IVF Patients" management.
    """
    permission_classes = [IsAuthenticated, IsIVFNurse]

    def get(self, request):
        from apps.patients.models import Patient
        ivf_patient_ids = IVFCycle.objects.values_list('patient_id', flat=True).distinct()
        patients = (
            Patient.objects.filter(id__in=ivf_patient_ids, is_active=True)
            .annotate(cycle_count=Count('ivf_cycles'))
            .order_by('last_name', 'first_name')
        )
        data = [
            {'id': p.id, 'patient_id': p.patient_id, 'first_name': p.first_name, 'last_name': p.last_name, 'cycle_count': p.cycle_count}
            for p in patients
        ]
        serializer = IVFPatientListSerializer(data=data, many=True)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)


class IVFVisitsListView(APIView):
    """
    List visits for patients who have at least one IVF cycle (IVF patient visits only).
    Used by the IVF dashboard for "IVF Patient Visits".
    """
    permission_classes = [IsAuthenticated, IsIVFNurse]

    def get(self, request):
        from apps.visits.models import Visit
        from apps.visits.serializers import VisitSerializer
        ivf_patient_ids = IVFCycle.objects.values_list('patient_id', flat=True).distinct()
        visits = (
            Visit.objects.filter(patient_id__in=ivf_patient_ids)
            .select_related('patient')
            .order_by('-created_at')
        )
        status_filter = request.query_params.get('status')
        if status_filter:
            visits = visits.filter(status=status_filter)
        serializer = VisitSerializer(visits, many=True)
        return Response(serializer.data)

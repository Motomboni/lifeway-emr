"""
Views for Admission, Ward, and Bed management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError as DRFValidationError, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .admission_models import Ward, Bed, Admission
from .admission_serializers import (
    WardSerializer,
    BedSerializer,
    BedListSerializer,
    AdmissionSerializer,
    AdmissionCreateSerializer,
    AdmissionUpdateSerializer,
    AdmissionTransferSerializer,
)
from apps.visits.models import Visit
from core.audit import AuditLog


class WardViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Ward management.
    
    All authenticated users can view wards.
    Only doctors can create/update/delete wards.
    """
    queryset = Ward.objects.all().order_by('name')
    serializer_class = WardSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter by active status if requested."""
        queryset = super().get_queryset()
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        return queryset
    
    def perform_create(self, serializer):
        """Create ward with audit logging."""
        user_role = getattr(self.request.user, 'role', None) or \
                   getattr(self.request.user, 'get_role', lambda: None)()
        
        if user_role != 'DOCTOR':
            raise PermissionDenied("Only doctors can create wards.")
        
        ward = serializer.save()
        
        AuditLog.log(
            user=self.request.user,
            role=user_role,
            action='ward.create',
            visit_id=None,
            resource_type='ward',
            resource_id=ward.id,
            request=self.request
        )
    
    def perform_update(self, serializer):
        """Update ward with audit logging."""
        user_role = getattr(self.request.user, 'role', None) or \
                   getattr(self.request.user, 'get_role', lambda: None)()
        
        if user_role != 'DOCTOR':
            raise PermissionDenied("Only doctors can update wards.")
        
        ward = serializer.save()
        
        AuditLog.log(
            user=self.request.user,
            role=user_role,
            action='ward.update',
            visit_id=None,
            resource_type='ward',
            resource_id=ward.id,
            request=self.request
        )
    
    @action(detail=True, methods=['get'])
    def beds(self, request, pk=None):
        """Get all beds in this ward."""
        ward = self.get_object()
        beds = Bed.objects.filter(ward=ward, is_active=True).order_by('bed_number')
        serializer = BedListSerializer(beds, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def available_beds(self, request, pk=None):
        """Get available beds in this ward."""
        ward = self.get_object()
        beds = Bed.objects.filter(ward=ward, is_available=True, is_active=True).order_by('bed_number')
        serializer = BedListSerializer(beds, many=True)
        return Response(serializer.data)


class BedViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Bed management.
    
    All authenticated users can view beds.
    Only doctors can create/update/delete beds.
    """
    queryset = Bed.objects.all().select_related('ward').order_by('ward', 'bed_number')
    serializer_class = BedSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter beds by ward, availability, etc."""
        queryset = super().get_queryset()
        
        ward_id = self.request.query_params.get('ward')
        if ward_id:
            queryset = queryset.filter(ward_id=ward_id)
        
        is_available = self.request.query_params.get('is_available')
        if is_available is not None:
            queryset = queryset.filter(is_available=is_available.lower() == 'true')
        
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset
    
    def perform_create(self, serializer):
        """Create bed with audit logging."""
        user_role = getattr(self.request.user, 'role', None) or \
                   getattr(self.request.user, 'get_role', lambda: None)()
        
        if user_role != 'DOCTOR':
            raise PermissionDenied("Only doctors can create beds.")
        
        bed = serializer.save()
        
        AuditLog.log(
            user=self.request.user,
            role=user_role,
            action='bed.create',
            visit_id=None,
            resource_type='bed',
            resource_id=bed.id,
            request=self.request,
            metadata={'ward_id': bed.ward_id, 'bed_number': bed.bed_number}
        )
    
    def perform_update(self, serializer):
        """Update bed with audit logging."""
        user_role = getattr(self.request.user, 'role', None) or \
                   getattr(self.request.user, 'get_role', lambda: None)()
        
        if user_role != 'DOCTOR':
            raise PermissionDenied("Only doctors can update beds.")
        
        bed = serializer.save()
        
        AuditLog.log(
            user=self.request.user,
            role=user_role,
            action='bed.update',
            visit_id=None,
            resource_type='bed',
            resource_id=bed.id,
            request=self.request
        )


class AdmissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Admission management - visit-scoped.
    
    Rules:
    - Visit-scoped: Admissions are tied to visits
    - Doctor-only creation
    - Admission status separate from visit status
    """
    serializer_class = AdmissionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get admissions for the specific visit."""
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            return Admission.objects.none()
        
        return Admission.objects.filter(visit_id=visit_id).select_related(
            'visit', 'ward', 'bed', 'admitting_doctor', 'visit__patient'
        )
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return AdmissionCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AdmissionUpdateSerializer
        elif self.action == 'transfer':
            return AdmissionTransferSerializer
        return AdmissionSerializer
    
    def get_visit(self):
        """Get visit from URL parameter (optimized: select_related patient)."""
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            raise NotFound("Visit ID is required.")
        
        try:
            return Visit.objects.select_related('patient').get(id=visit_id)
        except Visit.DoesNotExist:
            raise NotFound("Visit not found.")
    
    def create(self, request, *args, **kwargs):
        """Override create to handle visit from URL and remove it from request data."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Remove 'visit' from request data if present (it comes from URL parameter)
            data = request.data.copy()
            if 'visit' in data:
                del data['visit']
            
            logger.info(f"Creating admission - Request data: {data}")
            logger.info(f"Visit ID from URL: {kwargs.get('visit_id')}")
            
            serializer = self.get_serializer(data=data)
            if not serializer.is_valid():
                logger.error(f"Serializer validation errors: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except DRFValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error creating admission: {type(e).__name__}: {str(e)}", exc_info=True)
            # Return a more detailed error response
            return Response(
                {'detail': f'Error creating admission: {str(e)}', 'error_type': type(e).__name__},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def perform_create(self, serializer):
        """Create admission with validation and audit logging."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            visit = self.get_visit()
            
            # Ensure user is a doctor
            user_role = getattr(self.request.user, 'role', None) or \
                       getattr(self.request.user, 'get_role', lambda: None)()
            
            if user_role != 'DOCTOR':
                raise PermissionDenied("Only doctors can admit patients.")
            
            # Validate visit status
            if visit.status != 'OPEN':
                raise DRFValidationError("Can only admit patients with OPEN visits.")
            
            # Check if visit already has an admission
            if hasattr(visit, 'admission') and visit.admission:
                raise DRFValidationError("This visit already has an admission.")
            
            # Pass visit in context so serializer can access it
            serializer.context['visit'] = visit
            
            logger.info(f"Creating admission for visit {visit.id}, user {self.request.user.id}")
            logger.debug(f"Request data: {self.request.data}")
            
            # Create admission
            admission = serializer.save(
                visit=visit,
                admitting_doctor=self.request.user
            )
            
            logger.info(f"Admission {admission.id} created successfully")
            
            # Audit log
            try:
                AuditLog.log(
                    user=self.request.user,
                    role=user_role,
                    action='admission.create',
                    visit_id=visit.id,
                    resource_type='admission',
                    resource_id=admission.id,
                    request=self.request,
                    metadata={
                        'ward_id': admission.ward_id,
                        'bed_id': admission.bed_id,
                        'admission_type': admission.admission_type,
                        'admission_source': admission.admission_source,
                    }
                )
            except Exception as e:
                logger.error(f"Failed to create audit log for admission {admission.id}: {e}")
                # Don't fail the request if audit logging fails
        
            return admission
        except Exception as e:
            logger.error(f"Error creating admission: {type(e).__name__}: {str(e)}", exc_info=True)
            raise
    
    @action(detail=True, methods=['post'])
    def discharge(self, request, visit_id=None, pk=None):
        """Discharge the patient."""
        admission = self.get_object()
        
        # Ensure user is a doctor
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        if user_role != 'DOCTOR':
            raise PermissionDenied("Only doctors can discharge patients.")
        
        if admission.admission_status == 'DISCHARGED':
            raise DRFValidationError("Patient is already discharged.")
        
        discharge_date = request.data.get('discharge_date')
        if discharge_date:
            try:
                discharge_date = timezone.datetime.fromisoformat(discharge_date.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                discharge_date = timezone.now()
        else:
            discharge_date = timezone.now()
        
        admission.discharge(discharge_date=discharge_date)
        
        # If discharge summary exists, link it
        if hasattr(admission.visit, 'discharge_summary') and admission.visit.discharge_summary:
            discharge_summary = admission.visit.discharge_summary
            discharge_summary.admission = admission
            discharge_summary.save(update_fields=['admission'])
            admission.discharge_summary = discharge_summary
            admission.save(update_fields=['discharge_summary'])
        
        # Audit log
        AuditLog.log(
            user=request.user,
            role=user_role,
            action='admission.discharge',
            visit_id=admission.visit_id,
            resource_type='admission',
            resource_id=admission.id,
            request=request,
            metadata={
                'discharge_date': discharge_date.isoformat(),
            }
        )
        
        serializer = self.get_serializer(admission)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def transfer(self, request, visit_id=None, pk=None):
        """Transfer patient to different ward/bed."""
        admission = self.get_object()
        
        # Ensure user is a doctor
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        if user_role != 'DOCTOR':
            raise PermissionDenied("Only doctors can transfer patients.")
        
        serializer = AdmissionTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        new_ward = Ward.objects.get(id=serializer.validated_data['new_ward_id'])
        new_bed = Bed.objects.get(id=serializer.validated_data['new_bed_id'])
        transfer_notes = serializer.validated_data.get('transfer_notes', '')
        
        new_admission = admission.transfer(new_ward, new_bed, transfer_notes)
        
        # Audit log
        AuditLog.log(
            user=request.user,
            role=user_role,
            action='admission.transfer',
            visit_id=admission.visit_id,
            resource_type='admission',
            resource_id=new_admission.id,
            request=request,
            metadata={
                'from_ward_id': admission.ward_id,
                'from_bed_id': admission.bed_id,
                'to_ward_id': new_ward.id,
                'to_bed_id': new_bed.id,
            }
        )
        
        serializer = AdmissionSerializer(new_admission)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class InpatientListViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for listing all current inpatients across all visits.
    
    Shows all patients with admission_status = 'ADMITTED'.
    """
    queryset = Admission.objects.filter(
        admission_status='ADMITTED'
    ).select_related(
        'visit', 'ward', 'bed', 'admitting_doctor', 'visit__patient'
    ).order_by('-admission_date')
    
    serializer_class = AdmissionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter inpatients by ward if requested."""
        queryset = super().get_queryset()
        
        ward_id = self.request.query_params.get('ward')
        if ward_id:
            queryset = queryset.filter(ward_id=ward_id)
        
        return queryset


"""
Prescription ViewSet - strictly visit-scoped and consultation-dependent.

Endpoint: /api/v1/visits/{visit_id}/prescriptions/

Enforcement:
1. Visit-scoped: All operations require visit_id in URL
2. Consultation-dependent: Consultation must exist before prescriptions
3. Doctor: Can create prescriptions, view all
4. Payment must be CLEARED
5. Visit must be OPEN
6. Audit logging required
7. No standalone prescription flow allowed
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import (
    PermissionDenied,
    NotFound,
    ValidationError as DRFValidationError,
)
from django.shortcuts import get_object_or_404

from .models import Prescription, Drug
from .serializers import (
    PrescriptionSerializer,
    PrescriptionCreateSerializer,
    PrescriptionReadSerializer,
    DrugSerializer,
    DrugCreateSerializer,
    DrugUpdateSerializer,
)
from apps.visits.models import Visit
from apps.consultations.models import Consultation
from core.permissions import IsVisitOpen, IsPaymentCleared, IsVisitAccessible
from .permissions import IsDoctor, CanViewPrescription, CanDispensePrescription, CanManageDrugs
from core.audit import AuditLog


def log_prescription_action(
    user,
    action,
    visit_id,
    prescription_id=None,
    request=None,
    metadata=None
):
    """
    Log a prescription action to audit log.
    
    Args:
        user: User performing the action
        action: Action type (e.g., 'create', 'read')
        visit_id: Visit ID (required)
        prescription_id: Prescription ID if applicable
        request: Django request object (for IP/user agent)
        metadata: Additional metadata dict (no PHI)
    
    Returns:
        AuditLog instance
    """
    user_role = getattr(user, 'role', None) or getattr(user, 'get_role', lambda: 'UNKNOWN')()
    
    ip_address = None
    user_agent = ''
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
    
    audit_log = AuditLog(
        user=user,
        user_role=user_role,
        action=f'prescription.{action}',
        visit_id=visit_id,
        resource_type='prescription',
        resource_id=prescription_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata or {}
    )
    audit_log.save()
    return audit_log


class PrescriptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Prescriptions - visit-scoped and consultation-dependent.
    
    Rules enforced:
    - Visit-scoped architecture
    - Consultation-dependent (consultation must exist)
    - Doctor: Create prescriptions, view all
    - Payment must be CLEARED
    - Visit must be OPEN
    - Audit logging
    """
    
    def get_queryset(self):
        """
        Get prescriptions for the specific visit.
        Role-based filtering:
        - Doctor: Sees all prescriptions
        - Pharmacist: Sees all prescriptions (but limited fields in serializer)
        """
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            return Prescription.objects.none()
        
        return Prescription.objects.filter(visit_id=visit_id).select_related(
            'consultation',
            'prescribed_by',
            'dispensed_by'
        )
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        
        - Create: PrescriptionCreateSerializer (Doctor only)
        - Read: PrescriptionReadSerializer (role-based fields)
        """
        if self.action == 'create':
            return PrescriptionCreateSerializer
        else:
            return PrescriptionReadSerializer
    
    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        
        - Create: Doctor only (IsDoctor) + Payment + Visit Open
        - Update: Pharmacist only (CanDispensePrescription) + Payment + Visit Open
        - Read: Both roles (CanViewPrescription) - no payment/status check for reads
        """
        if self.action == 'create':
            permission_classes = [
                IsDoctor,
                IsVisitOpen,
                IsPaymentCleared,
            ]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [
                CanDispensePrescription,
                IsVisitOpen,
                IsPaymentCleared,
            ]
        else:
            # Read operations: Allow authenticated users (for billing/audit purposes)
            from rest_framework.permissions import IsAuthenticated
            permission_classes = [
                IsAuthenticated,
                IsVisitAccessible,
            ]
        
        return [permission() for permission in permission_classes]
    
    def get_visit(self):
        """Get and validate visit from URL parameter."""
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            raise DRFValidationError("visit_id is required in URL")
        
        visit = get_object_or_404(Visit, pk=visit_id)
        self.request.visit = visit
        return visit
    
    def get_consultation(self, visit):
        """
        Get consultation for the visit.
        Prescriptions REQUIRE consultation context.
        """
        consultation = Consultation.objects.filter(visit=visit).first()
        
        if not consultation:
            raise DRFValidationError(
                "Consultation must exist before creating prescriptions. "
                "Please create a consultation first."
            )
        
        return consultation
    
    def check_visit_status(self, visit):
        """Ensure visit is OPEN before allowing mutations."""
        if visit.status == 'CLOSED':
            raise PermissionDenied(
                detail="Cannot create or modify prescriptions for a CLOSED visit. "
                       "Closed visits are immutable per EMR rules.",
                code='visit_closed'
            )
    
    def check_payment_status(self, visit):
        """Ensure payment is cleared before allowing prescriptions."""
        if not visit.is_payment_cleared():
            raise PermissionDenied(
                detail="Payment must be cleared before creating prescriptions. "
                       "Current payment status: {status}".format(
                           status=visit.payment_status
                       ),
                code='payment_not_cleared'
            )
    
    def perform_create(self, serializer):
        """
        Create prescription with strict enforcement.
        
        Rules:
        1. Only Doctor can create (enforced by IsDoctor permission)
        2. Visit must be OPEN
        3. Payment must be CLEARED
        4. Consultation must exist
        5. prescribed_by set to authenticated user (doctor)
        6. Audit log created
        """
        visit = self.get_visit()
        
        # Enforce visit status
        self.check_visit_status(visit)
        
        # Enforce payment status
        self.check_payment_status(visit)
        
        # Get consultation (required)
        consultation = self.get_consultation(visit)
        
        # Check user role
        user_role = getattr(self.request.user, 'role', None) or \
                   getattr(self.request.user, 'get_role', lambda: None)()
        
        if user_role != 'DOCTOR':
            raise PermissionDenied(
                detail="Only doctors can create prescriptions.",
                code='role_forbidden'
            )
        
        # Create prescription
        prescription = serializer.save(
            visit=visit,
            consultation=consultation,
            prescribed_by=self.request.user,
            status='PENDING'
        )
        
        # Audit log
        log_prescription_action(
            user=self.request.user,
            action='create',
            visit_id=visit.id,
            prescription_id=prescription.id,
            request=self.request
        )
        
        return prescription
    
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve prescription with role-based field visibility.
        
        Doctor: Sees all fields
        Pharmacist: Sees limited fields (no consultation details)
        """
        prescription = self.get_object()
        visit = prescription.visit
        
        # Audit log
        log_prescription_action(
            user=request.user,
            action='read',
            visit_id=visit.id,
            prescription_id=prescription.id,
            request=request
        )
        
        serializer = self.get_serializer(prescription)
        return Response(serializer.data)
    
    def list(self, request, *args, **kwargs):
        """
        List prescriptions for visit.
        Role-based field visibility applied via serializer.
        """
        try:
            visit = self.get_visit()
            
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            
            # Audit log for listing prescriptions
            log_prescription_action(
                user=request.user,
                action='list',
                visit_id=visit.id,
                request=request
            )
            
            return Response(serializer.data)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error listing prescriptions: {str(e)}", exc_info=True)
            raise DRFValidationError(f"Error listing prescriptions: {str(e)}")
    
    def perform_update(self, serializer):
        """
        Update prescription.
        Per EMR rules, only Pharmacist can update (dispense).
        Doctor cannot update prescriptions (only view).
        """
        prescription = self.get_object()
        visit = prescription.visit
        
        # Enforce visit status
        self.check_visit_status(visit)
        
        # Enforce payment status
        self.check_payment_status(visit)
        
        # Check user role
        user_role = getattr(self.request.user, 'role', None) or \
                   getattr(self.request.user, 'get_role', lambda: None)()
        
        if user_role == 'PHARMACIST':
            # Pharmacist can dispense
            from django.utils import timezone
            updated_prescription = serializer.save(
                dispensed_by=self.request.user,
                dispensed_date=timezone.now(),
                dispensed=True,
                status='DISPENSED'
            )
            
            # Audit log
            log_prescription_action(
                user=self.request.user,
                action='dispense',
                visit_id=visit.id,
                prescription_id=updated_prescription.id,
                request=self.request
            )
            
            return updated_prescription
        else:
            # Doctor cannot update prescriptions (only view)
            raise PermissionDenied(
                detail="Doctors cannot update prescriptions. "
                       "Only Pharmacist can dispense medication.",
                code='role_forbidden'
            )
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete prescription.
        Per EMR rules, prescriptions should not be deleted (soft-delete only).
        This endpoint is disabled for compliance.
        """
        raise PermissionDenied(
            detail="Prescriptions cannot be deleted. "
                   "Use status CANCELLED instead for compliance.",
            code='delete_forbidden'
        )


class DrugViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Drug catalog management - Pharmacist only.
    
    Endpoint: /api/v1/drugs/
    
    Rules enforced:
    - Pharmacist-only access (create, update, delete)
    - All authenticated users can view (for reference when creating prescriptions)
    - Audit logging required
    """
    
    queryset = Drug.objects.all().select_related('created_by').prefetch_related('inventory')
    permission_classes = [CanManageDrugs]
    pagination_class = None  # Disable pagination for drug catalog (typically small dataset)
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        """
        if self.action == 'create':
            return DrugCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return DrugUpdateSerializer
        else:
            return DrugSerializer
    
    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        - Create, Update, Delete: Pharmacist only
        - Read: All authenticated users (for reference)
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [CanManageDrugs]
        else:
            # Read operations: Allow all authenticated users
            from rest_framework.permissions import IsAuthenticated
            permission_classes = [IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        """
        Create drug entry.
        Sets created_by to current user (pharmacist).
        """
        drug = serializer.save(created_by=self.request.user)
        
        # Audit log
        user_role = getattr(self.request.user, 'role', None) or getattr(self.request.user, 'get_role', lambda: 'UNKNOWN')()
        
        AuditLog.objects.create(
            user=self.request.user,
            user_role=user_role,
            action='drug.create',
            resource_type='drug',
            resource_id=drug.id,
            ip_address=self._get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')[:500],
            metadata={
                'drug_name': drug.name,
                'drug_code': drug.drug_code or '',
            }
        )
        
        return drug
    
    def perform_update(self, serializer):
        """
        Update drug entry.
        """
        drug = serializer.save()
        
        # Audit log
        user_role = getattr(self.request.user, 'role', None) or getattr(self.request.user, 'get_role', lambda: 'UNKNOWN')()
        
        AuditLog.objects.create(
            user=self.request.user,
            user_role=user_role,
            action='drug.update',
            resource_type='drug',
            resource_id=drug.id,
            ip_address=self._get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')[:500],
            metadata={
                'drug_name': drug.name,
                'drug_code': drug.drug_code or '',
            }
        )
        
        return drug
    
    def perform_destroy(self, instance):
        """
        Delete drug entry (soft delete by setting is_active=False).
        Per EMR rules, we don't hard delete, but we can deactivate.
        """
        # Soft delete: set is_active to False
        instance.is_active = False
        instance.save()
        
        # Audit log
        user_role = getattr(self.request.user, 'role', None) or getattr(self.request.user, 'get_role', lambda: 'UNKNOWN')()
        
        AuditLog.objects.create(
            user=self.request.user,
            user_role=user_role,
            action='drug.delete',
            resource_type='drug',
            resource_id=instance.id,
            ip_address=self._get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')[:500],
            metadata={
                'drug_name': instance.name,
                'drug_code': instance.drug_code or '',
            }
        )
    
    def _get_client_ip(self):
        """Get client IP address from request."""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return self.request.META.get('REMOTE_ADDR')

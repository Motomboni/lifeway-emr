"""
Lab Order ViewSet - strictly visit-scoped and consultation-dependent.

Endpoint: /api/v1/visits/{visit_id}/laboratory/

Enforcement:
1. Visit-scoped: All operations require visit_id in URL
2. Consultation-dependent: Consultation must exist before lab orders
3. Doctor: Can create orders, view all (including results)
4. Lab Tech: Can only update results, cannot create orders
5. Payment must be CLEARED
6. Visit must be OPEN
7. Audit logging required
8. No standalone lab flow allowed
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

from .models import LabOrder
from .serializers import (
    LabOrderSerializer,
    LabOrderCreateSerializer,
    LabOrderResultSerializer,
    LabOrderReadSerializer,
)
from apps.visits.models import Visit
from apps.consultations.models import Consultation
from core.permissions import IsVisitOpen, IsPaymentCleared, IsVisitAccessible
from .permissions import (
    IsDoctorOrLabTech,
    CanCreateLabOrder,
    CanUpdateLabResult,
    CanViewLabOrder,
)
from core.audit import AuditLog


def log_lab_order_action(
    user,
    action,
    visit_id,
    lab_order_id=None,
    request=None,
    metadata=None
):
    """
    Log a lab order action to audit log.
    
    Args:
        user: User performing the action
        action: Action type (e.g., 'create', 'update_result', 'read')
        visit_id: Visit ID (required)
        lab_order_id: Lab Order ID if applicable
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
        action=f'lab_order.{action}',
        visit_id=visit_id,
        resource_type='lab_order',
        resource_id=lab_order_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata or {}
    )
    audit_log.save()
    return audit_log


class LabOrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Lab Orders - visit-scoped and consultation-dependent.
    
    Rules enforced:
    - Visit-scoped architecture
    - Consultation-dependent (consultation must exist)
    - Doctor: Create orders, view all
    - Lab Tech: Update results only, cannot create
    - Payment must be CLEARED
    - Visit must be OPEN
    - Audit logging
    """
    # Restrict lookup to digits so "results" path is not mistaken for a PK
    lookup_value_regex = r'\d+'
    
    def initial(self, request, *args, **kwargs):
        """
        Ensure request.visit is set early for permission checks.
        """
        visit_id = kwargs.get("visit_id")
        if visit_id and not hasattr(request, "visit"):
            try:
                visit = Visit.objects.get(pk=visit_id)
                request.visit = visit
            except Visit.DoesNotExist:
                # Let permissions/views handle missing visit
                pass
        super().initial(request, *args, **kwargs)
    
    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        
        - Create: Doctor only (CanCreateLabOrder) + Payment + Visit Open
        - Update: Lab Tech only (CanUpdateLabResult) + Payment + Visit Open
        - Read: Both roles (CanViewLabOrder) - no payment/status check for reads
        """
        if self.action == 'create':
            permission_classes = [
                CanCreateLabOrder,
                IsVisitOpen,
                IsPaymentCleared,
            ]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [
                CanUpdateLabResult,
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
    
    def get_queryset(self):
        """
        Get lab orders for the specific visit.
        Role-based filtering:
        - Doctor: Sees all lab orders
        - Lab Tech: Sees all lab orders (but limited fields in serializer)
        """
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            return LabOrder.objects.none()
        
        # Use select_related for forward relations only
        # Note: 'result' is a reverse OneToOne from LabResult, so we can't use select_related on it
        return LabOrder.objects.filter(visit_id=visit_id).select_related(
            'consultation',
            'ordered_by'
        )
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action and user role.
        
        - Create: LabOrderCreateSerializer (Doctor only)
        - Update (result): LabOrderResultSerializer (Lab Tech only)
        - Read: LabOrderReadSerializer (role-based fields)
        """
        user_role = getattr(self.request.user, 'role', None) or \
                   getattr(self.request.user, 'get_role', lambda: None)()
        
        if self.action == 'create':
            return LabOrderCreateSerializer
        elif self.action in ['update', 'partial_update']:
            # Check if Lab Tech is updating result
            if user_role == 'LAB_TECH':
                return LabOrderResultSerializer
            # Doctor cannot update (only view)
            return LabOrderReadSerializer
        else:
            return LabOrderReadSerializer
    
    def get_serializer_context(self):
        """Add visit to serializer context."""
        context = super().get_serializer_context()
        # Ensure visit is in context for serializer
        if hasattr(self.request, 'visit'):
            context['visit'] = self.request.visit
        elif 'visit_id' in self.kwargs:
            try:
                context['visit'] = Visit.objects.get(pk=self.kwargs['visit_id'])
            except Visit.DoesNotExist:
                pass
        return context
    
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
        Lab orders REQUIRE consultation context.
        """
        consultation = Consultation.objects.filter(visit=visit).first()
        
        if not consultation:
            raise DRFValidationError(
                "Consultation must exist before creating lab orders. "
                "Please create a consultation first."
            )
        
        return consultation
    
    def check_visit_status(self, visit):
        """Ensure visit is OPEN before allowing mutations."""
        if visit.status == 'CLOSED':
            raise PermissionDenied(
                detail="Cannot create or modify lab orders for a CLOSED visit. "
                       "Closed visits are immutable per EMR rules.",
                code='visit_closed'
            )
    
    def check_payment_status(self, visit):
        """Ensure payment is cleared before allowing lab orders."""
        if not visit.is_payment_cleared():
            raise PermissionDenied(
                detail="Payment must be cleared before creating lab orders. "
                       "Current payment status: {status}".format(
                           status=visit.payment_status
                       ),
                code='payment_not_cleared'
            )
    
    def perform_create(self, serializer):
        """
        Create lab order with strict enforcement.
        
        Rules:
        1. Only Doctor can create (enforced by CanCreateLabOrder)
        2. Visit must be OPEN
        3. Payment must be CLEARED
        4. Consultation must exist
        5. ordered_by set to authenticated user (doctor)
        6. Audit log created
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
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
                    detail="Only doctors can create lab orders. "
                           "Lab Tech can only update results.",
                    code='role_forbidden'
                )
            
            # Create lab order
            lab_order = serializer.save(
                visit=visit,
                consultation=consultation,
                ordered_by=self.request.user,
                status=LabOrder.Status.ORDERED
            )
            
            # REQUIRED VIEWSET ENFORCEMENT: Audit log
            # Ensure user_role is a string (required by AuditLog model)
            if not user_role:
                user_role = 'UNKNOWN'
            
            AuditLog.log(
                user=self.request.user,
                role=user_role,
                action="LAB_ORDER_CREATED",
                visit_id=self.kwargs["visit_id"],
                resource_type="lab_order",
                resource_id=lab_order.id,
                request=self.request
            )
            
            return lab_order
        except Exception as e:
            logger.error(f"Error creating lab order: {str(e)}", exc_info=True)
            raise DRFValidationError(f"Error creating lab order: {str(e)}")
    
    def perform_update(self, serializer):
        """
        Update lab order with role-based enforcement.
        
        Rules:
        1. Lab Tech can only update results
        2. Doctor cannot update (only view)
        3. Visit must be OPEN
        4. Payment must be CLEARED
        5. Audit log created
        """
        lab_order = self.get_object()
        visit = lab_order.visit
        
        # Enforce visit status
        self.check_visit_status(visit)
        
        # Enforce payment status
        self.check_payment_status(visit)
        
        # Check user role
        user_role = getattr(self.request.user, 'role', None) or \
                   getattr(self.request.user, 'get_role', lambda: None)()
        
        if user_role == 'LAB_TECH':
            # Lab Tech can update results
            from django.utils import timezone
            updated_lab_order = serializer.save(
                resulted_by=self.request.user,
                result_date=timezone.now(),
                status='COMPLETED' if serializer.validated_data.get('result') else 'IN_PROGRESS'
            )
            
            # Audit log
            log_lab_order_action(
                user=self.request.user,
                action='update_result',
                visit_id=visit.id,
                lab_order_id=updated_lab_order.id,
                request=self.request
            )
            
            return updated_lab_order
        else:
            # Doctor cannot update lab orders (only view)
            raise PermissionDenied(
                detail="Doctors cannot update lab orders. "
                       "Only Lab Tech can post results.",
                code='role_forbidden'
            )
    
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve lab order with role-based field visibility.
        
        Doctor: Sees all fields
        Lab Tech: Sees limited fields (no consultation details)
        """
        lab_order = self.get_object()
        visit = lab_order.visit
        
        # Audit log
        log_lab_order_action(
            user=request.user,
            action='read',
            visit_id=visit.id,
            lab_order_id=lab_order.id,
            request=request
        )
        
        serializer = self.get_serializer(lab_order)
        return Response(serializer.data)
    
    def list(self, request, *args, **kwargs):
        """
        List lab orders for visit.
        Role-based field visibility applied via serializer.
        """
        try:
            visit = self.get_visit()
            
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            
            return Response(serializer.data)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error listing lab orders: {str(e)}", exc_info=True)
            raise DRFValidationError(f"Error listing lab orders: {str(e)}")
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete lab order.
        Per EMR rules, lab orders should not be deleted (soft-delete only).
        This endpoint is disabled for compliance.
        """
        raise PermissionDenied(
            detail="Lab orders cannot be deleted. "
                   "Use status CANCELLED instead for compliance.",
            code='delete_forbidden'
        )

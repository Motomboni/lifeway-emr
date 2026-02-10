"""
Lab Result ViewSet - strictly visit-scoped.

Endpoint: /api/v1/visits/{visit_id}/laboratory/results/

Enforcement:
1. Visit-scoped: All operations require visit_id in URL
2. Lab Tech: Can create results (immutable once created)
3. Doctor: Can view results (read-only)
4. Payment must be CLEARED
5. Visit must be OPEN
6. Audit logging required
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.exceptions import (
    PermissionDenied,
    ValidationError as DRFValidationError,
)
from django.shortcuts import get_object_or_404

from .models import LabResult, LabOrder
from .result_serializers import LabResultCreateSerializer, LabResultReadSerializer
from apps.visits.models import Visit
from core.permissions import IsVisitOpen, IsPaymentCleared, IsVisitAccessible
from .permissions import IsDoctorOrLabTech, CanUpdateLabResult
from core.audit import AuditLog
from apps.notifications.utils import send_lab_result_notification


class LabResultViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Lab Results - visit-scoped.
    
    Rules enforced:
    - Visit-scoped architecture
    - Lab Tech: Create results (immutable once created)
    - Doctor: View results (read-only)
    - Payment must be CLEARED
    - Visit must be OPEN
    - Audit logging
    """
    http_method_names = ['get', 'post', 'head', 'options']
    
    def initial(self, request, *args, **kwargs):
        """
        Ensure request.visit is set early for permission checks.
        """
        # Try to get visit_id from kwargs (router) or request (middleware)
        visit_id = kwargs.get("visit_id") or getattr(request, "visit_id", None)
        if visit_id and not hasattr(request, "visit"):
            try:
                visit = Visit.objects.get(pk=visit_id)
                request.visit = visit
            except Visit.DoesNotExist:
                # Let permissions/views handle missing visit
                pass
        # Also ensure visit_id is in kwargs for consistency
        if visit_id and "visit_id" not in kwargs:
            kwargs["visit_id"] = visit_id
        super().initial(request, *args, **kwargs)

    def get_queryset(self):
        """
        Get lab results for the specific visit.
        Filter by lab orders that belong to the visit.
        """
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            return LabResult.objects.none()
        
        # Get all lab orders for this visit
        lab_orders = LabOrder.objects.filter(visit_id=visit_id)
        lab_order_ids = lab_orders.values_list('id', flat=True)
        
        return LabResult.objects.filter(
            lab_order_id__in=lab_order_ids
        ).select_related(
            'lab_order',
            'recorded_by'
        )

    def list(self, request, *args, **kwargs):
        """
        List lab results for a visit with defensive error handling.
        """
        import logging

        logger = logging.getLogger(__name__)
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except Exception as exc:
            logger.error("Error listing lab results", exc_info=True)
            raise DRFValidationError(f"Error listing lab results: {exc}")
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        
        - Create: LabResultCreateSerializer (Lab Tech only)
        - Read: LabResultReadSerializer (both roles)
        """
        if self.action == 'create':
            return LabResultCreateSerializer
        else:
            return LabResultReadSerializer
    
    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        
        - Create: Lab Tech only + Payment + Visit Open
        - Read: Both roles (Doctor and Lab Tech) - no payment/status check for reads
        """
        if self.action == 'create':
            permission_classes = [
                CanUpdateLabResult,  # Lab Tech only
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
        # Try to get visit_id from kwargs (router) or request (middleware)
        visit_id = self.kwargs.get('visit_id') or getattr(self.request, "visit_id", None)
        if not visit_id:
            raise DRFValidationError("visit_id is required in URL")
        
        visit = get_object_or_404(Visit, pk=visit_id)
        self.request.visit = visit
        # Ensure visit_id is in kwargs for consistency
        if "visit_id" not in self.kwargs:
            self.kwargs["visit_id"] = visit_id
        return visit
    
    def check_visit_status(self, visit):
        """Ensure visit is OPEN before allowing mutations."""
        if visit.status == 'CLOSED':
            raise PermissionDenied(
                detail="Cannot create lab results for a CLOSED visit. "
                       "Closed visits are immutable per EMR rules.",
                code='visit_closed'
            )
    
    def check_payment_status(self, visit):
        """Ensure payment is cleared before allowing lab results."""
        if not visit.is_payment_cleared():
            raise PermissionDenied(
                detail="Payment must be cleared before creating lab results. "
                       "Current payment status: {status}".format(
                           status=visit.payment_status
                       ),
                code='payment_not_cleared'
            )
    
    def check_user_role(self, request):
        """Ensure user is a Lab Tech for creating results."""
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        if user_role != 'LAB_TECH':
            raise PermissionDenied(
                detail="Only Lab Technicians can create lab results.",
                code='role_forbidden'
            )
    
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
    
    def create(self, request, *args, **kwargs):
        """
        Create lab result - explicitly allow POST.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Ensure visit is set before create
            if not hasattr(request, 'visit') and 'visit_id' in kwargs:
                try:
                    request.visit = Visit.objects.get(pk=kwargs['visit_id'])
                except Visit.DoesNotExist:
                    pass
            
            return super().create(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in create method: {str(e)}", exc_info=True)
            raise DRFValidationError(f"Error creating lab result: {str(e)}")
    
    def perform_create(self, serializer):
        """
        Create lab result with strict enforcement.
        
        Rules:
        1. Only Lab Tech can create (enforced by CanUpdateLabResult permission)
        2. Visit must be OPEN
        3. Payment must be CLEARED
        4. LabOrder must be ORDERED
        5. LabOrder must belong to visit
        6. Result must not already exist (immutability)
        7. recorded_by set to authenticated user (Lab Tech)
        8. Audit log created
        """
        visit = self.get_visit()
        
        # Enforce visit status
        self.check_visit_status(visit)
        
        # Enforce payment status
        self.check_payment_status(visit)
        
        # Enforce user role
        self.check_user_role(self.request)
        
        # Add visit to context for serializer validation
        serializer.context['visit'] = visit
        serializer.context['request'] = self.request
        
        # Create lab result
        lab_result = serializer.save()
        
        # Update lab order status to RESULT_READY
        lab_result.lab_order.status = 'RESULT_READY'
        lab_result.lab_order.save()
        
        # REQUIRED VIEWSET ENFORCEMENT: Audit log
        user_role = getattr(self.request.user, 'role', None) or \
                   getattr(self.request.user, 'get_role', lambda: None)()
        
        # Ensure user_role is a string (required by AuditLog model)
        if not user_role:
            user_role = 'UNKNOWN'
        
        AuditLog.log(
            user=self.request.user,
            role=user_role,
            action="LAB_RESULT_CREATED",
            visit_id=self.kwargs["visit_id"],
            resource_type="lab_result",
            resource_id=lab_result.id,
            request=self.request
        )
        
        # Send email notification
        try:
            patient = visit.patient
            if patient and patient.email:
                send_lab_result_notification(lab_result)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send lab result notification email: {e}")
        
        # Send SMS notification
        try:
            patient = visit.patient
            if patient and patient.phone:
                from apps.notifications.sms_utils import send_lab_result_sms
                send_lab_result_sms(lab_result)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send lab result notification SMS: {e}")
        
        return lab_result
    
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve lab result.
        
        Both Doctor and Lab Tech can view results.
        """
        lab_result = self.get_object()
        visit = lab_result.lab_order.visit
        
        # Audit log
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        # Ensure user_role is a string (required by AuditLog model)
        if not user_role:
            user_role = 'UNKNOWN'
        
        AuditLog.log(
            user=request.user,
            role=user_role,
            action="LAB_RESULT_READ",
            visit_id=visit.id,
            resource_type="lab_result",
            resource_id=lab_result.id,
            request=request
        )
        
        serializer = self.get_serializer(lab_result)
        return Response(serializer.data)
    
    def list(self, request, *args, **kwargs):
        """
        List lab results for visit.
        Returns empty array if no results exist (404 is not appropriate for empty list).
        """
        try:
            visit = self.get_visit()
            
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            
            return Response(serializer.data)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error listing lab results: {str(e)}", exc_info=True)
            raise DRFValidationError(f"Error listing lab results: {str(e)}")
    
    def update(self, request, *args, **kwargs):
        """
        Update lab result.
        
        Per EMR rules, lab results are immutable once created.
        """
        raise PermissionDenied(
            detail="Lab results are immutable once created. "
                   "Cannot modify existing results.",
            code='immutable'
        )
    
    def partial_update(self, request, *args, **kwargs):
        """
        Partially update lab result.
        
        Per EMR rules, lab results are immutable once created.
        """
        raise PermissionDenied(
            detail="Lab results are immutable once created. "
                   "Cannot modify existing results.",
            code='immutable'
        )
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete lab result.
        
        Per EMR rules, lab results should not be deleted.
        This endpoint is disabled for compliance.
        """
        raise PermissionDenied(
            detail="Lab results cannot be deleted. "
                   "Results are immutable per EMR rules.",
            code='delete_forbidden'
        )

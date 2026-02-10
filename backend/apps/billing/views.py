"""
Payment ViewSet - visit-scoped payment processing.

Per EMR Rules:
- Payment is visit-scoped
- Receptionist processes payments
- Payment must be CLEARED before clinical actions
- All payment actions are audited
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import (
    PermissionDenied,
    ValidationError as DRFValidationError,
)
from django.shortcuts import get_object_or_404

from .models import Payment
from .serializers import (
    PaymentSerializer,
    PaymentCreateSerializer,
    PaymentClearSerializer,
)
from .permissions import CanProcessPayment
from apps.visits.models import Visit
from core.permissions import IsVisitOpen
from core.audit import AuditLog


class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Payment processing - visit-scoped.
    
    Endpoint: /api/v1/visits/{visit_id}/payments/
    
    Rules enforced:
    - Visit-scoped architecture
    - Receptionist-only processing
    - Visit must be OPEN
    - Audit logging
    """
    
    def get_queryset(self):
        """Get payments for the specific visit."""
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            return Payment.objects.none()
        
        return Payment.objects.filter(visit_id=visit_id).select_related(
            'visit',
            'processed_by'
        )
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        
        - Create: PaymentCreateSerializer
        - Clear: PaymentClearSerializer
        - Other: PaymentSerializer
        """
        if self.action == 'create':
            return PaymentCreateSerializer
        elif self.action == 'clear':
            return PaymentClearSerializer
        else:
            return PaymentSerializer
    
    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        
        - Create/Clear/Update: Receptionist only + Visit Open
        - Read: Authenticated users
        
        Per EMR Rules:
        - Only Receptionists can create, edit, or modify billing records
        - Closed visits are billing read-only
        """
        if self.action in ['create', 'clear', 'update', 'partial_update']:
            permission_classes = [CanProcessPayment, IsVisitOpen]
        else:
            from rest_framework.permissions import IsAuthenticated
            permission_classes = [IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def check_visit_not_closed(self, visit):
        """
        Ensure visit is not CLOSED before allowing billing modifications.
        
        Per EMR Rules:
        - Closed visits are billing read-only
        """
        if visit.status == 'CLOSED':
            raise PermissionDenied(
                detail="Cannot modify billing for a CLOSED visit. "
                       "Closed visits are billing read-only per EMR rules.",
                code='visit_closed_billing_readonly'
            )
    
    def get_visit(self):
        """Get and validate visit from URL parameter."""
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            raise DRFValidationError("visit_id is required in URL")
        
        visit = get_object_or_404(Visit, pk=visit_id)
        self.request.visit = visit
        return visit
    
    def check_user_role(self, request):
        """Ensure user is a Receptionist."""
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        if user_role != 'RECEPTIONIST':
            raise PermissionDenied(
                detail="Only Receptionists can process payments.",
                code='role_forbidden'
            )
    
    def perform_create(self, serializer):
        """
        Create payment with strict enforcement.
        
        Rules:
        1. Only Receptionist can create (enforced by CanProcessPayment)
        2. Visit must be OPEN
        3. processed_by set to authenticated user (Receptionist)
        4. Audit log created
        """
        visit = self.get_visit()
        
        # Enforce user role
        self.check_user_role(self.request)
        
        # Create payment
        payment = serializer.save(
            visit=visit,
            processed_by=self.request.user,
            status=serializer.validated_data.get('status', 'PENDING')
        )
        
        # REQUIRED VIEWSET ENFORCEMENT: Audit log
        user_role = getattr(self.request.user, 'role', None) or \
                   getattr(self.request.user, 'get_role', lambda: None)()
        
        AuditLog.log(
            user=self.request.user,
            role=user_role,
            action="PAYMENT_CREATED",
            visit_id=self.kwargs["visit_id"],
            resource_type="payment",
            resource_id=payment.id,
            request=self.request
        )
        
        return payment
    
    @action(detail=True, methods=['post'], url_path='clear')
    def clear(self, request, visit_id=None, pk=None):
        """
        Clear a payment (mark as CLEARED).
        
        POST /api/v1/visits/{visit_id}/payments/{id}/clear/
        
        Rules:
        1. Only Receptionist can clear
        2. Visit must be OPEN
        3. Visit must not be CLOSED (billing read-only)
        4. Payment status updated to CLEARED
        5. Visit payment_status updated to CLEARED
        6. Audit log created
        """
        visit = self.get_visit()
        payment = self.get_object()
        
        # Enforce user role
        self.check_user_role(request)
        
        # Enforce visit not closed (billing read-only)
        self.check_visit_not_closed(visit)
        
        # Validate payment belongs to visit
        if payment.visit_id != visit.id:
            raise DRFValidationError(
                "Payment does not belong to this visit."
            )
        
        # Validate payment is not already cleared
        if payment.status == 'CLEARED':
            raise DRFValidationError(
                "Payment is already cleared."
            )
        
        # Update payment
        serializer = PaymentClearSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        payment.status = 'CLEARED'
        if serializer.validated_data.get('transaction_reference'):
            payment.transaction_reference = serializer.validated_data['transaction_reference']
        if serializer.validated_data.get('notes'):
            payment.notes = serializer.validated_data['notes']
        payment.save()
        
        # Update visit payment status based on billing summary
        # Payment.save() already updates visit.payment_status, but we ensure it's current
        from .billing_service import BillingService
        summary = BillingService.compute_billing_summary(visit)
        visit.payment_status = summary.payment_status
        visit.save(update_fields=['payment_status'])
        
        # Audit log
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        AuditLog.log(
            user=request.user,
            role=user_role,
            action="PAYMENT_CLEARED",
            visit_id=visit_id,
            resource_type="payment",
            resource_id=payment.id,
            request=request
        )
        
        return Response(
            {
                'message': 'Payment cleared successfully.',
                'payment': PaymentSerializer(payment).data,
                'visit': {
                    'id': visit.id,
                    'payment_status': visit.payment_status
                }
            },
            status=status.HTTP_200_OK
        )
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve payment with audit logging."""
        payment = self.get_object()
        
        # Audit log
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        AuditLog.log(
            user=request.user,
            role=user_role,
            action="PAYMENT_READ",
            visit_id=self.kwargs["visit_id"],
            resource_type="payment",
            resource_id=payment.id,
            request=request
        )
        
        serializer = self.get_serializer(payment)
        return Response(serializer.data)
    
    def list(self, request, *args, **kwargs):
        """List payments for visit."""
        visit = self.get_visit()
        
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        """
        Update payment - Receptionist only.
        
        Per EMR Rules:
        - Only Receptionists can modify billing records
        - Closed visits are billing read-only
        """
        visit = self.get_visit()
        self.check_user_role(request)
        self.check_visit_not_closed(visit)
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        """
        Partially update payment - Receptionist only.
        
        Per EMR Rules:
        - Only Receptionists can modify billing records
        - Closed visits are billing read-only
        """
        visit = self.get_visit()
        self.check_user_role(request)
        self.check_visit_not_closed(visit)
        return super().partial_update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete payment.
        
        Per EMR rules, payments should not be deleted.
        Use status REFUNDED instead.
        """
        raise PermissionDenied(
            detail="Payments cannot be deleted. Use status REFUNDED for compliance.",
            code='delete_forbidden'
        )

"""
Views for Referral model.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError as DRFValidationError
from django.shortcuts import get_object_or_404
from .models import Referral
from .serializers import (
    ReferralSerializer,
    ReferralCreateSerializer,
    ReferralUpdateSerializer,
)
from .permissions import CanCreateReferral, CanViewReferral, CanUpdateReferral
from apps.visits.models import Visit
from apps.consultations.models import Consultation
from core.permissions import IsVisitOpen, IsPaymentCleared, IsVisitAccessible
from core.audit import AuditLog


def log_referral_action(
    user,
    action,
    visit_id,
    referral_id=None,
    request=None,
    metadata=None
):
    """
    Log a referral action to audit log.
    
    Args:
        user: User performing the action
        action: Action type (e.g., 'create', 'update', 'read')
        visit_id: Visit ID (required)
        referral_id: Referral ID if applicable
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
        action=f'referral.{action}',
        visit_id=visit_id,
        resource_type='referral',
        resource_id=referral_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata or {}
    )
    audit_log.save()
    return audit_log


class ReferralViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Referral management - visit-scoped and consultation-dependent.
    
    Rules enforced:
    - Visit-scoped architecture
    - Consultation-dependent (consultation must exist)
    - Doctor-only creation
    - Payment must be CLEARED for creation
    - Visit must be OPEN for creation
    - Status updates allowed even for CLOSED visits
    - Audit logging
    """
    
    def get_queryset(self):
        """Get referrals for the specific visit."""
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            return Referral.objects.none()
        
        return Referral.objects.filter(visit_id=visit_id).select_related(
            'visit',
            'consultation',
            'referred_by'
        )
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return ReferralCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ReferralUpdateSerializer
        else:
            return ReferralSerializer
    
    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        
        - Create: Doctor only + Payment + Visit Open
        - Update: Doctor/Receptionist + Visit Accessible (allows status updates for closed visits)
        - Read: All authenticated users + Visit Accessible
        """
        if self.action == 'create':
            permission_classes = [
                CanCreateReferral,
                IsVisitOpen,
                IsPaymentCleared,
            ]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [
                CanUpdateReferral,
                IsVisitAccessible,  # Allows updates even for closed visits
            ]
        else:
            # Read operations: All authenticated users, visit accessible
            permission_classes = [
                CanViewReferral,
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
        Referrals REQUIRE consultation context.
        """
        consultation = Consultation.objects.filter(visit=visit).first()
        
        if not consultation:
            raise DRFValidationError(
                "Consultation must exist before creating referrals. "
                "Please create a consultation first."
            )
        
        return consultation
    
    def perform_create(self, serializer):
        """Create referral with validation and audit logging."""
        visit = self.get_visit()
        consultation = self.get_consultation(visit)
        
        # Ensure visit is OPEN
        if visit.status != 'OPEN':
            raise DRFValidationError(
                "Referrals can only be created for OPEN visits."
            )
        
        # Ensure payment is cleared
        if not visit.is_payment_cleared():
            raise DRFValidationError(
                "Payment must be cleared before creating referrals."
            )
        
        # Create referral
        referral = serializer.save()
        
        # Audit log
        log_referral_action(
            user=self.request.user,
            action='create',
            visit_id=visit.id,
            referral_id=referral.id,
            request=self.request,
            metadata={
                'specialty': referral.specialty,
                'specialist_name': referral.specialist_name,
                'urgency': referral.urgency,
            }
        )
        
        return referral
    
    def perform_update(self, serializer):
        """Update referral with audit logging."""
        referral = serializer.save()
        visit = referral.visit
        
        # Audit log
        log_referral_action(
            user=self.request.user,
            action='update',
            visit_id=visit.id,
            referral_id=referral.id,
            request=self.request,
            metadata={
                'status': referral.status,
                'updated_fields': list(serializer.validated_data.keys()),
            }
        )
        
        return referral
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a referral."""
        referral = self.get_object()
        
        # Audit log
        log_referral_action(
            user=request.user,
            action='read',
            visit_id=referral.visit_id,
            referral_id=referral.id,
            request=request,
        )
        
        serializer = self.get_serializer(referral)
        return Response(serializer.data)
    
    def list(self, request, *args, **kwargs):
        """List referrals for the visit."""
        visit = self.get_visit()
        
        # Audit log
        log_referral_action(
            user=request.user,
            action='list',
            visit_id=visit.id,
            request=request,
        )
        
        return super().list(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'], url_path='accept')
    def accept_referral(self, request, visit_id=None, pk=None):
        """Accept a referral."""
        referral = self.get_object()
        
        if referral.status != 'PENDING':
            return Response(
                {'error': f'Referral is already {referral.status.lower()}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        referral.accept()
        
        # Audit log
        log_referral_action(
            user=request.user,
            action='accept',
            visit_id=referral.visit_id,
            referral_id=referral.id,
            request=request,
        )
        
        serializer = self.get_serializer(referral)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='complete')
    def complete_referral(self, request, visit_id=None, pk=None):
        """Complete a referral."""
        referral = self.get_object()
        
        if referral.status != 'ACCEPTED':
            return Response(
                {'error': 'Referral must be ACCEPTED before it can be completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        referral.complete()
        
        # Audit log
        log_referral_action(
            user=request.user,
            action='complete',
            visit_id=referral.visit_id,
            referral_id=referral.id,
            request=request,
        )
        
        serializer = self.get_serializer(referral)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """Disable DELETE - referrals cannot be deleted per EMR rules."""
        return Response(
            {'error': 'Referrals cannot be deleted. Use status update to cancel instead.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

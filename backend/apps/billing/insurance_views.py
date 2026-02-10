"""
Insurance ViewSets - visit-scoped insurance management.

Per EMR Rules:
- Receptionist-only access
- Visit-scoped insurance data
- Insurance alters payment responsibility, does NOT bypass billing
- All actions logged to AuditLog
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import (
    PermissionDenied,
    ValidationError as DRFValidationError,
)
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .insurance_models import HMOProvider, VisitInsurance
from .insurance_serializers import (
    HMOProviderSerializer,
    HMOProviderCreateSerializer,
    VisitInsuranceSerializer,
    VisitInsuranceCreateSerializer,
    VisitInsuranceUpdateSerializer,
)
from .permissions import CanProcessPayment
from apps.visits.models import Visit
from core.permissions import IsVisitOpen
from core.audit import AuditLog


class HMOProviderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for HMO Provider management - Receptionist only.
    
    Endpoint: /api/v1/billing/hmo-providers/
    
    Rules enforced:
    - Receptionist-only access
    - Audit logging
    """
    
    queryset = HMOProvider.objects.all().order_by('name')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return HMOProviderCreateSerializer
        else:
            return HMOProviderSerializer
    
    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        
        - All actions: Receptionist only
        """
        permission_classes = [CanProcessPayment]
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        """
        Create HMO Provider with strict enforcement.
        
        Rules:
        1. Only Receptionist can create (enforced by CanProcessPayment)
        2. created_by set to authenticated user (Receptionist)
        3. Audit log created
        """
        # Enforce user role
        user_role = getattr(self.request.user, 'role', None) or \
                   getattr(self.request.user, 'get_role', lambda: None)()
        
        if user_role != 'RECEPTIONIST':
            raise PermissionDenied(
                detail="Only Receptionists can manage HMO providers.",
                code='role_forbidden'
            )
        
        provider = serializer.save(created_by=self.request.user)
        
        # Audit log
        AuditLog.log(
            user=self.request.user,
            role=user_role,
            action="HMO_PROVIDER_CREATED",
            resource_type="hmo_provider",
            resource_id=provider.id,
            request=self.request
        )
        
        return provider
    
    def perform_update(self, serializer):
        """Update HMO Provider with audit logging."""
        provider = serializer.save()
        
        # Audit log
        user_role = getattr(self.request.user, 'role', None) or \
                   getattr(self.request.user, 'get_role', lambda: None)()
        
        AuditLog.log(
            user=self.request.user,
            role=user_role,
            action="HMO_PROVIDER_UPDATED",
            resource_type="hmo_provider",
            resource_id=provider.id,
            request=self.request
        )
        
        return provider


class VisitInsuranceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Visit Insurance - visit-scoped, Receptionist only.
    
    Endpoint: /api/v1/visits/{visit_id}/insurance/
    
    Rules enforced:
    - Visit-scoped architecture
    - Receptionist-only access
    - Visit must be OPEN
    - Audit logging
    """
    
    def get_queryset(self):
        """Get insurance for the specific visit."""
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            return VisitInsurance.objects.none()
        
        return VisitInsurance.objects.filter(visit_id=visit_id).select_related(
            'visit',
            'provider',
            'created_by'
        )
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return VisitInsuranceCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return VisitInsuranceUpdateSerializer
        else:
            return VisitInsuranceSerializer
    
    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        
        - Create/Update: Receptionist only + Visit Open
        - Read: Authenticated users
        """
        if self.action in ['create', 'update', 'partial_update']:
            permission_classes = [CanProcessPayment, IsVisitOpen]
        else:
            from rest_framework.permissions import IsAuthenticated
            permission_classes = [IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
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
                detail="Only Receptionists can manage insurance records.",
                code='role_forbidden'
            )
    
    def check_visit_not_closed(self, visit):
        """Ensure visit is not CLOSED before allowing insurance modifications."""
        if visit.status == 'CLOSED':
            raise PermissionDenied(
                detail="Cannot modify insurance for a CLOSED visit. "
                       "Closed visits are immutable per EMR rules.",
                code='visit_closed'
            )
    
    def perform_create(self, serializer):
        """
        Create Visit Insurance with strict enforcement.
        
        Rules:
        1. Only Receptionist can create (enforced by CanProcessPayment)
        2. Visit must be OPEN (enforced by IsVisitOpen)
        3. Visit must not be CLOSED
        4. created_by set to authenticated user (Receptionist)
        5. Audit log created
        """
        visit = self.get_visit()
        
        # Enforce user role
        self.check_user_role(self.request)
        
        # Enforce visit not closed
        self.check_visit_not_closed(visit)
        
        # Check if insurance already exists for this visit (OneToOneField)
        if VisitInsurance.objects.filter(visit=visit).exists():
            raise DRFValidationError(
                "Insurance record already exists for this visit. "
                "Use PUT/PATCH to update instead."
            )
        
        # Create insurance record
        insurance = serializer.save(
            visit=visit,
            created_by=self.request.user
        )
        
        # Audit log
        user_role = getattr(self.request.user, 'role', None) or \
                   getattr(self.request.user, 'get_role', lambda: None)()
        
        AuditLog.log(
            user=self.request.user,
            role=user_role,
            action="VISIT_INSURANCE_CREATED",
            visit_id=visit.id,
            resource_type="visit_insurance",
            resource_id=insurance.id,
            request=self.request
        )
        
        return insurance
    
    def perform_update(self, serializer):
        """
        Update Visit Insurance with strict enforcement.
        
        Rules:
        1. Only Receptionist can update
        2. Visit must be OPEN
        3. Visit must not be CLOSED
        4. Audit log created
        """
        visit = self.get_visit()
        insurance = self.get_object()
        
        # Enforce user role
        self.check_user_role(self.request)
        
        # Enforce visit not closed
        self.check_visit_not_closed(visit)
        
        # Update approval_date if status is being changed to APPROVED
        if 'approval_status' in serializer.validated_data:
            if serializer.validated_data['approval_status'] == 'APPROVED':
                serializer.validated_data['approval_date'] = timezone.now()
        
        insurance = serializer.save()
        
        # When insurance is approved, update visit.payment_status so clinical actions are allowed
        if getattr(insurance, 'approval_status', None) == 'APPROVED':
            from .billing_service import BillingService
            summary = BillingService.compute_billing_summary(visit)
            new_status = summary.payment_status
            if new_status in ('SETTLED', 'INSURANCE_CLAIMED', 'PAID', 'PARTIALLY_PAID'):
                if visit.payment_status != new_status:
                    visit.payment_status = new_status
                    visit.save(update_fields=['payment_status'])
            elif getattr(summary, 'is_fully_covered_by_insurance', False):
                # Fully covered by insurance => SETTLED so payment guard allows consultation
                if visit.payment_status != 'SETTLED':
                    visit.payment_status = 'SETTLED'
                    visit.save(update_fields=['payment_status'])
        
        # Audit log
        user_role = getattr(self.request.user, 'role', None) or \
                   getattr(self.request.user, 'get_role', lambda: None)()
        
        AuditLog.log(
            user=self.request.user,
            role=user_role,
            action="VISIT_INSURANCE_UPDATED",
            visit_id=visit.id,
            resource_type="visit_insurance",
            resource_id=insurance.id,
            request=self.request
        )
        
        return insurance
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve insurance with audit logging."""
        insurance = self.get_object()
        
        # Audit log
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        AuditLog.log(
            user=request.user,
            role=user_role,
            action="VISIT_INSURANCE_READ",
            visit_id=self.kwargs["visit_id"],
            resource_type="visit_insurance",
            resource_id=insurance.id,
            request=request
        )
        
        serializer = self.get_serializer(insurance)
        return Response(serializer.data)
    
    def list(self, request, *args, **kwargs):
        """
        List insurance for visit (should be single record due to OneToOneField).
        
        Returns single object if exists, or empty response if not found.
        This matches frontend expectations for GET /visits/{visit_id}/insurance/
        """
        visit = self.get_visit()
        
        queryset = self.get_queryset()
        insurance = queryset.first()
        
        if insurance:
            serializer = self.get_serializer(insurance)
            return Response(serializer.data)
        else:
            # Return 404 if no insurance found (matches frontend expectation)
            from rest_framework.exceptions import NotFound
            raise NotFound("No insurance record found for this visit.")
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete insurance record.
        
        Per EMR rules, insurance records should not be deleted.
        Use soft-delete or status update instead.
        """
        raise PermissionDenied(
            detail="Insurance records cannot be deleted. "
                   "Update approval_status to REJECTED instead for compliance.",
            code='delete_forbidden'
        )

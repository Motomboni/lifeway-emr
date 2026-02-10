"""
Visit ViewSet - visit management and closure.

Endpoint: /api/v1/visits/

Enforcement:
1. Doctor-only closure
2. Consultation required before closure
3. Immutability enforcement (CLOSED visits cannot be modified)
4. Audit logging mandatory
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import (
    PermissionDenied,
    ValidationError as DRFValidationError,
)
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError

from .models import Visit
from .serializers import (
    VisitSerializer,
    VisitCreateSerializer,
    VisitReadSerializer,
)
from apps.consultations.models import Consultation
from apps.patients.models import Patient
from core.permissions import IsDoctor
from core.audit import AuditLog


def log_visit_action(
    user,
    action,
    visit_id,
    request=None,
    metadata=None
):
    """
    Log a visit action to audit log.
    
    Args:
        user: User performing the action
        action: Action type (e.g., 'close', 'read')
        visit_id: Visit ID (required)
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
        action=f'visit.{action}',
        visit_id=visit_id,
        resource_type='visit',
        resource_id=visit_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata or {}
    )
    audit_log.save()
    return audit_log


class VisitViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Visit management.
    
    Rules enforced:
    - Receptionist: Can create visits
    - Doctor-only closure
    - Consultation required before closure
    - Immutability enforcement
    - Audit logging
    """
    
    queryset = Visit.objects.all().select_related('patient', 'closed_by')
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        
        - Create: VisitCreateSerializer
        - Read: VisitReadSerializer
        - Other: VisitSerializer
        """
        if self.action == 'create':
            return VisitCreateSerializer
        elif self.action in ['retrieve', 'list']:
            return VisitReadSerializer
        else:
            return VisitSerializer
    
    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        
        - Close: Doctor only
        - Create: Receptionist (or authenticated for now)
        - Other actions: Authenticated users
        """
        if self.action == 'close':
            permission_classes = [IsDoctor]
        else:
            # Default permissions for other actions
            from rest_framework.permissions import IsAuthenticated
            permission_classes = [IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def create(self, request, *args, **kwargs):
        """
        Create visit with audit logging.
        
        Override to ensure visit is fully saved and returned with proper serializer.
        """
        from django.db import transaction
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Step 1: Validate data
            username = getattr(request.user, 'username', 'unknown')
            print(f"DEBUG: Creating visit for user {username}")
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Step 2: Extract payment info
            payment_type = serializer.validated_data.get('payment_type', 'CASH')
            if payment_type == 'INSURANCE':
                initial_payment_status = 'INSURANCE_PENDING'
            else:
                initial_payment_status = serializer.validated_data.get('payment_status', 'UNPAID')
            
            # Step 3: Perform database operations in a small transaction with retries for SQLite
            import time
            from django.db import OperationalError
            
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    with transaction.atomic():
                        visit = serializer.save(
                            status='OPEN',
                            payment_type=payment_type,
                            payment_status=initial_payment_status
                        )
                        print(f"DEBUG: Visit saved: {visit.id}")
                        
                        # Create Bill for the visit
                        from apps.billing.bill_models import Bill, InsurancePolicy
                        
                        # If insurance visit, try to find insurance policy first
                        insurance_policy = None
                        is_insurance_backed = False
                        if payment_type == 'INSURANCE':
                            insurance_policy = InsurancePolicy.objects.filter(
                                patient=visit.patient,
                                is_active=True
                            ).first()
                            # Only set is_insurance_backed if we have an insurance policy
                            is_insurance_backed = (insurance_policy is not None)
                        
                        bill_defaults = {
                            'status': initial_payment_status,
                            'created_by': self.request.user,
                            'is_insurance_backed': is_insurance_backed,
                            'insurance_policy': insurance_policy  # Set insurance_policy if found
                        }
                        
                        bill, created = Bill.objects.get_or_create(
                            visit=visit,
                            defaults=bill_defaults
                        )
                        
                        # If bill already existed and we need to update it for insurance
                        if not created and payment_type == 'INSURANCE':
                            if insurance_policy and not bill.insurance_policy:
                                bill.insurance_policy = insurance_policy
                                bill.is_insurance_backed = True
                                bill.save(update_fields=['insurance_policy', 'is_insurance_backed'])
                            elif not insurance_policy:
                                # Insurance visit but no policy found - bill remains non-insurance
                                # This is okay, the visit payment_status will still be INSURANCE_PENDING
                                pass
                        
                        # Auto-create VisitInsurance from patient's InsurancePolicy if insurance visit
                        if payment_type == 'INSURANCE':
                            from apps.billing.insurance_models import VisitInsurance, HMOProvider
                            
                            # Check if VisitInsurance already exists for this visit
                            if not VisitInsurance.objects.filter(visit=visit).exists():
                                # If insurance_policy wasn't found earlier, try to find it again
                                if not insurance_policy:
                                    insurance_policy = InsurancePolicy.objects.filter(
                                        patient=visit.patient,
                                        is_active=True
                                    ).first()
                                
                                if insurance_policy:
                                    try:
                                        # Find or create HMOProvider from InsuranceProvider
                                        insurance_provider = insurance_policy.provider
                                        hmo_provider, created = HMOProvider.objects.get_or_create(
                                            name=insurance_provider.name,
                                            defaults={
                                                'code': insurance_provider.code or '',
                                                'contact_person': insurance_provider.contact_person or '',
                                                'contact_phone': insurance_provider.contact_phone or '',
                                                'contact_email': insurance_provider.contact_email or '',
                                                'address': insurance_provider.address or '',
                                                'is_active': insurance_provider.is_active,
                                                'created_by': self.request.user,
                                            }
                                        )
                                        
                                        # Create VisitInsurance from InsurancePolicy
                                        visit_insurance = VisitInsurance.objects.create(
                                            visit=visit,
                                            provider=hmo_provider,
                                            policy_number=insurance_policy.policy_number,
                                            coverage_type=insurance_policy.coverage_type,
                                            coverage_percentage=insurance_policy.coverage_percentage,
                                            approval_status='PENDING',
                                            notes=f'Auto-created from patient insurance policy registered on {insurance_policy.valid_from}',
                                            created_by=self.request.user,
                                        )
                                        logger.info(
                                            f"Auto-created VisitInsurance {visit_insurance.id} for visit {visit.id} "
                                            f"from patient insurance policy {insurance_policy.id}"
                                        )
                                    except Exception as e:
                                        # Log error but don't fail visit creation
                                        logger.error(
                                            f"Failed to auto-create VisitInsurance for visit {visit.id}: {str(e)}",
                                            exc_info=True
                                        )
                                else:
                                    logger.warning(
                                        f"Visit {visit.id} created with payment_type='INSURANCE' but no active "
                                        f"insurance policy found for patient {visit.patient.id}. "
                                        f"VisitInsurance will not be auto-created."
                                    )
                    
                    # If we reach here, transaction succeeded
                    break
                except OperationalError as e:
                    if "database is locked" in str(e) and attempt < max_retries - 1:
                        print(f"DEBUG: Database locked, retrying visit creation (attempt {attempt + 1})...")
                        time.sleep(1) # Wait 1s before retry
                        continue
                    raise # Re-raise if other error or max retries reached

            # Step 4: Post-transaction operations
            visit.refresh_from_db()
            
            # Audit logging
            user_role = getattr(self.request.user, 'role', None) or \
                       getattr(self.request.user, 'get_role', lambda: None)()
            
            AuditLog.log(
                user=self.request.user,
                role=user_role,
                action="VISIT_CREATED",
                visit_id=visit.id,
                resource_type="visit",
                resource_id=visit.id,
                request=self.request
            )
            
            # Return response
            read_serializer = VisitReadSerializer(visit)
            response_data = read_serializer.data
            headers = self.get_success_headers(response_data)
            return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)
            
        except DRFValidationError:
            raise
        except Exception as e:
            logger.error(f"Error creating visit: {str(e)}", exc_info=True)
            print(f"DEBUG: Error creating visit: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {"detail": f"Database error or server error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve visit with audit logging.
        
        All authenticated users can view visits (for clinical context).
        Receptionist can view visits they created or need to process payments for.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Get the visit ID from kwargs
        visit_id = kwargs.get('pk')
        logger.info(f"Retrieving visit {visit_id} for user {request.user.id} ({request.user.role})")
        
        try:
            # Check if visit exists in database
            visit_exists = Visit.objects.filter(id=visit_id).exists()
            logger.info(f"Visit {visit_id} exists in database: {visit_exists}")
            
            if not visit_exists:
                from rest_framework.exceptions import NotFound
                logger.warning(f"Visit {visit_id} does not exist in database")
                raise NotFound(f"Visit {visit_id} not found")
            
            visit = self.get_object()
            logger.info(f"Successfully retrieved visit {visit_id}")
        except Exception as e:
            # Log the error for debugging
            logger.error(f"Error retrieving visit {visit_id}: {str(e)}", exc_info=True)
            raise
        
        # Audit log
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        AuditLog.log(
            user=request.user,
            role=user_role,
            action="VISIT_READ",
            visit_id=visit.id,
            resource_type="visit",
            resource_id=visit.id,
            request=request
        )
        
        serializer = self.get_serializer(visit)
        return Response(serializer.data)
    
    def list(self, request, *args, **kwargs):
        """
        List visits with optional filtering.
        
        Query parameters:
        - patient: Filter by patient ID
        - status: Filter by status (OPEN, CLOSED)
        - payment_status: Filter by payment status
        """
        queryset = self.get_queryset()
        
        # Filter by patient if provided
        patient_id = request.query_params.get('patient', None)
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        
        # Filter by status if provided
        status = request.query_params.get('status', None)
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by payment_status if provided
        payment_status = request.query_params.get('payment_status', None)
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def check_user_role(self, request):
        """Ensure user is a Doctor."""
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        if user_role != 'DOCTOR':
            raise PermissionDenied(
                detail="Only doctors can close visits.",
                code='role_forbidden'
            )
    
    def check_consultation_exists(self, visit):
        """Ensure visit has consultation before closure."""
        if not visit.has_consultation():
            raise DRFValidationError(
                "Visit must have at least one consultation before it can be closed."
            )
    
    def check_visit_not_already_closed(self, visit):
        """Ensure visit is not already closed."""
        if visit.is_closed():
            raise DRFValidationError(
                "Visit is already CLOSED. Closed visits are immutable per EMR rules."
            )
    
    def check_outstanding_balance(self, visit):
        """
        Ensure visit can be closed based on billing rules.
        
        Per EMR Rules:
        - If CASH visit: Bill outstanding balance must be 0
        - If INSURANCE visit: Bill status must be INSURANCE_PENDING or SETTLED
        
        Uses centralized BillingService for deterministic computation.
        Returns human-readable error messages.
        """
        from apps.billing.billing_service import BillingService
        
        can_close, reason = BillingService.can_close_visit(visit)
        
        if not can_close:
            raise DRFValidationError({
                'detail': reason,
                'visit_id': visit.id,
                'payment_type': visit.payment_type,
            })
    
    @action(detail=True, methods=['post'], url_path='close')
    def close(self, request, pk=None):
        """
        Close a visit.
        
        Rules:
        1. Only Doctor can close visit
        2. Visit must have consultation
        3. Visit must not already be CLOSED
        4. Billing validation:
           - If CASH visit: Bill outstanding balance must be 0
           - If INSURANCE visit: Bill status must be INSURANCE_PENDING or SETTLED
        5. Audit log created
        
        Once CLOSED:
        - No edits allowed
        - No new orders allowed
        - No new prescriptions allowed
        - Billing is read-only
        - Read-only access only
        """
        visit = self.get_object()
        
        # Enforce user role
        self.check_user_role(request)
        
        # Enforce visit not already closed
        self.check_visit_not_already_closed(visit)
        
        # Enforce consultation exists
        self.check_consultation_exists(visit)
        
        # Enforce no outstanding balance (HARD RULE)
        self.check_outstanding_balance(visit)
        
        # Close the visit
        visit.status = 'CLOSED'
        visit.closed_by = request.user
        visit.closed_at = timezone.now()
        
        # Save with validation
        try:
            visit.save()
        except DjangoValidationError as e:
            raise DRFValidationError(str(e))
        
        # Audit log
        log_visit_action(
            user=request.user,
            action='close',
            visit_id=visit.id,
            request=request,
            metadata={
                'visit_id': visit.id,
                'status': 'CLOSED',
                'closed_by': request.user.id,
                'closed_at': visit.closed_at.isoformat()
            }
        )
        
        return Response(
            {
                'message': 'Visit closed successfully.',
                'visit': {
                    'id': visit.id,
                    'status': visit.status,
                    'closed_by': visit.closed_by.id,
                    'closed_at': visit.closed_at.isoformat()
                }
            },
            status=status.HTTP_200_OK
        )
    
    def update(self, request, *args, **kwargs):
        """
        Update visit.
        
        Per EMR rules, CLOSED visits cannot be modified.
        """
        visit = self.get_object()
        
        if visit.is_closed():
            raise PermissionDenied(
                detail="Cannot modify a CLOSED visit. Closed visits are immutable per EMR rules.",
                code='visit_closed'
            )
        
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        """
        Partially update visit.
        
        Per EMR rules, CLOSED visits cannot be modified.
        """
        visit = self.get_object()
        
        if visit.is_closed():
            raise PermissionDenied(
                detail="Cannot modify a CLOSED visit. Closed visits are immutable per EMR rules.",
                code='visit_closed'
            )
        
        return super().partial_update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete visit.
        
        Per EMR rules, visits should not be deleted (soft-delete only).
        This endpoint is disabled for compliance.
        """
        raise PermissionDenied(
            detail="Visits cannot be deleted. Use closure instead for compliance.",
            code='delete_forbidden'
        )

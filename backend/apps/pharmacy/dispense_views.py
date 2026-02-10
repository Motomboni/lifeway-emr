"""
Pharmacy Dispensing ViewSet - dedicated dispensing endpoint.

Endpoint: /api/v1/visits/{visit_id}/pharmacy/dispense/

Enforcement:
1. Pharmacist-only access
2. Prescription must exist
3. Visit must be OPEN
4. Payment must be CLEARED
5. Doctor cannot dispense
6. Audit logging mandatory
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
from django.utils import timezone

from .models import Prescription
from apps.visits.models import Visit
from core.permissions import IsVisitOpen, IsPaymentCleared
from .permissions import CanDispensePrescription
from core.audit import AuditLog


def log_dispense_action(
    user,
    action,
    visit_id,
    prescription_id,
    request=None,
    metadata=None
):
    """
    Log a dispensing action to audit log.
    
    Args:
        user: User performing the action
        action: Action type (e.g., 'dispense')
        visit_id: Visit ID (required)
        prescription_id: Prescription ID (required)
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
        action=f'pharmacy.{action}',
        visit_id=visit_id,
        resource_type='prescription',
        resource_id=prescription_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata or {}
    )
    audit_log.save()
    return audit_log


class DispenseViewSet(viewsets.ViewSet):
    """
    ViewSet for Pharmacy Dispensing - dedicated dispensing endpoint.
    
    Endpoint: /api/v1/visits/{visit_id}/pharmacy/dispense/
    
    Rules enforced:
    - Pharmacist-only access
    - Prescription must exist
    - Visit must be OPEN
    - Payment must be CLEARED
    - Doctor cannot dispense
    - Audit logging mandatory
    """
    
    permission_classes = [
        CanDispensePrescription,
    ]
    
    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        Visit and payment checks are done in the create method
        to ensure visit is loaded from middleware first.
        """
        return [permission() for permission in self.permission_classes]
    
    def check_visit_status(self, visit):
        """Ensure visit is OPEN before allowing dispensing."""
        if visit.status == 'CLOSED':
            raise PermissionDenied(
                detail="Cannot dispense medication for a CLOSED visit. "
                       "Closed visits are immutable per EMR rules.",
                code='visit_closed'
            )
    
    def check_payment_status(self, visit):
        """Ensure payment is cleared before allowing dispensing."""
        if not visit.is_payment_cleared():
            raise PermissionDenied(
                detail="Payment must be cleared before dispensing medication. "
                       "Current payment status: {status}".format(
                           status=visit.payment_status
                       ),
                code='payment_not_cleared'
            )
    
    def check_user_role(self, request):
        """Ensure user is a Pharmacist."""
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        if user_role != 'PHARMACIST':
            raise PermissionDenied(
                detail="Only Pharmacists can dispense medication. "
                       "Doctors cannot dispense.",
                code='role_forbidden'
            )
    
    def create(self, request, visit_id=None):
        """
        Dispense medication for a prescription.
        
        Request body:
        {
            "prescription_id": 1,
            "dispensing_notes": "Dispensed as prescribed. Patient counseled."
        }
        
        Rules:
        1. Only Pharmacist can dispense
        2. Prescription must exist and belong to visit
        3. Visit must be OPEN
        4. Payment must be CLEARED
        5. Prescription must not already be dispensed
        6. Audit log created
        """
        # Get visit from request attribute (set by middleware) or from URL
        visit = getattr(request, 'visit', None)
        if not visit:
            # Try to extract from URL path
            path_parts = request.path.split('/')
            try:
                if 'visits' in path_parts:
                    visits_index = path_parts.index('visits')
                    if visits_index + 1 < len(path_parts):
                        visit_id_str = path_parts[visits_index + 1]
                        visit_id = int(visit_id_str)
                        visit = get_object_or_404(Visit, pk=visit_id)
                        request.visit = visit
            except (ValueError, IndexError):
                raise DRFValidationError("visit_id is required in URL")
        
        if not visit:
            raise DRFValidationError("visit_id is required in URL")
        
        # Enforce user role first (before visit/payment checks)
        self.check_user_role(request)
        
        # Enforce visit status
        self.check_visit_status(visit)
        
        # Enforce payment status
        self.check_payment_status(visit)
        
        # Get prescription_id from request body
        prescription_id = request.data.get('prescription_id')
        if not prescription_id:
            raise DRFValidationError(
                {"prescription_id": "prescription_id is required in request body."}
            )
        
        # Get prescription and ensure it belongs to visit
        try:
            prescription = Prescription.objects.get(
                id=prescription_id,
                visit=visit
            )
        except Prescription.DoesNotExist:
            raise NotFound(
                detail=f"Prescription {prescription_id} not found for visit {visit.id}."
            )
        
        # Check if already dispensed
        if prescription.dispensed:
            raise DRFValidationError(
                {"prescription_id": f"Prescription {prescription_id} has already been dispensed."}
            )
        
        # Check if prescription is cancelled
        if prescription.status == 'CANCELLED':
            raise DRFValidationError(
                {"prescription_id": f"Cannot dispense a cancelled prescription."}
            )
        
        # Dispense the medication
        dispensing_notes = request.data.get('dispensing_notes', '')
        
        prescription.dispensed = True
        prescription.dispensed_date = timezone.now()
        prescription.dispensed_by = request.user
        prescription.status = 'DISPENSED'
        if dispensing_notes:
            prescription.dispensing_notes = dispensing_notes
        prescription.save()
        
        # Audit log
        log_dispense_action(
            user=request.user,
            action='dispense',
            visit_id=visit.id,
            prescription_id=prescription.id,
            request=request,
            metadata={
                'prescription_id': prescription.id,
                'drug': prescription.drug,
                'status': 'DISPENSED'
            }
        )
        
        # Return dispensed prescription
        from .serializers import PrescriptionReadSerializer
        serializer = PrescriptionReadSerializer(prescription)
        
        return Response(
            {
                'message': 'Medication dispensed successfully.',
                'prescription': serializer.data
            },
            status=status.HTTP_200_OK
        )

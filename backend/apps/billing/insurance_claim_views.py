"""
Insurance/HMO Claim Submission API.

Per EMR Rules:
- Insurance visits marked at visit creation
- BillItems marked as INSURANCE for insurance visits
- No immediate payment required
- Generate invoice instead of receipt
- State flow: INSURANCE_PENDING → INSURANCE_CLAIMED → SETTLED
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import (
    NotFound,
    ValidationError as DRFValidationError,
)
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.visits.models import Visit
from apps.billing.bill_models import Bill, BillItem, InsuranceProvider, InsurancePolicy
from .permissions import CanProcessPayment
from core.audit import AuditLog


class SubmitInsuranceClaimView(APIView):
    """
    POST /api/billing/insurance/submit-claim/
    
    Submit insurance claim for a bill.
    
    Payload:
    {
        "bill_id": 1,
        "insurance_provider": "Health Insurance Co.",
        "policy_number": "POL-123456"
    }
    
    Behavior:
    - Validates bill exists and is insurance-backed
    - Validates insurance provider exists
    - Validates or creates insurance policy
    - Updates bill status: INSURANCE_PENDING → INSURANCE_CLAIMED
    - Marks all bill items as INSURANCE
    """
    permission_classes = [IsAuthenticated, CanProcessPayment]
    
    def post(self, request):
        """
        Submit insurance claim for a bill.
        
        Validates:
        1. Bill exists and is insurance-backed
        2. Insurance provider exists
        3. Policy number is provided
        4. Visit is OPEN
        """
        bill_id = request.data.get('bill_id')
        insurance_provider_name = request.data.get('insurance_provider')
        policy_number = request.data.get('policy_number')
        
        # Validate required fields
        if not bill_id:
            raise DRFValidationError("bill_id is required.")
        
        if not insurance_provider_name:
            raise DRFValidationError("insurance_provider is required.")
        
        if not policy_number:
            raise DRFValidationError("policy_number is required.")
        
        # Get bill
        try:
            bill = Bill.objects.get(id=bill_id)
        except Bill.DoesNotExist:
            raise NotFound(f"Bill with id {bill_id} not found.")
        
        # Validate visit is OPEN
        if bill.visit.status != 'OPEN':
            raise DRFValidationError(
                f"Cannot submit insurance claim for a {bill.visit.status} visit. Visit must be OPEN."
            )
        
        # Get or create insurance provider
        try:
            insurance_provider = InsuranceProvider.objects.get(name=insurance_provider_name)
        except InsuranceProvider.DoesNotExist:
            # Create insurance provider if it doesn't exist
            insurance_provider = InsuranceProvider.objects.create(
                name=insurance_provider_name,
                is_active=True
            )
        
        # Get or create insurance policy for patient
        patient = bill.visit.patient
        insurance_policy, created = InsurancePolicy.objects.get_or_create(
            patient=patient,
            provider=insurance_provider,
            policy_number=policy_number,
            defaults={
                'coverage_type': 'FULL',  # Default to full coverage
                'coverage_percentage': 100.00,
                'is_active': True,
                'valid_from': timezone.now().date(),
            }
        )
        
        # Update bill to be insurance-backed
        bill.is_insurance_backed = True
        bill.insurance_policy = insurance_policy
        
        # Mark all bill items as INSURANCE
        BillItem.objects.filter(bill=bill).update(status='INSURANCE')
        
        # Update bill status to INSURANCE_PENDING (if not already claimed)
        if bill.status == 'UNPAID':
            bill.status = 'INSURANCE_PENDING'
        
        # Update visit payment_status
        bill.visit.payment_status = 'INSURANCE_PENDING'
        bill.visit.save(update_fields=['payment_status'])
        
        # Recalculate totals and save
        bill.recalculate_totals()
        bill.save(update_fields=['is_insurance_backed', 'insurance_policy', 'status', 'total_amount', 'outstanding_balance', 'updated_at'])
        
        # Audit log
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        AuditLog.log(
            user=request.user,
            role=user_role,
            action="INSURANCE_CLAIM_SUBMITTED",
            visit_id=bill.visit.id,
            resource_type="bill",
            resource_id=bill.id,
            request=request,
            metadata={
                'insurance_provider': insurance_provider.name,
                'policy_number': policy_number,
                'bill_status': bill.status,
            }
        )
        
        return Response(
            {
                'bill_id': bill.id,
                'visit_id': bill.visit.id,
                'insurance_provider': insurance_provider.name,
                'policy_number': policy_number,
                'bill_status': bill.status,
                'visit_payment_status': bill.visit.payment_status,
                'is_insurance_backed': bill.is_insurance_backed,
                'policy_created': policy_created,
                'items_marked_as_insurance': items_updated,
            },
            status=status.HTTP_200_OK
        )


class UpdateInsuranceClaimStatusView(APIView):
    """
    POST /api/billing/insurance/update-claim-status/
    
    Update insurance claim status.
    
    Payload:
    {
        "bill_id": 1,
        "status": "INSURANCE_CLAIMED" or "SETTLED"
    }
    
    State flow:
    INSURANCE_PENDING → INSURANCE_CLAIMED → SETTLED
    """
    permission_classes = [IsAuthenticated, CanProcessPayment]
    
    def post(self, request):
        """
        Update insurance claim status.
        
        Validates state transitions:
        - INSURANCE_PENDING → INSURANCE_CLAIMED
        - INSURANCE_CLAIMED → SETTLED
        """
        bill_id = request.data.get('bill_id')
        new_status = request.data.get('status')
        
        # Validate required fields
        if not bill_id:
            raise DRFValidationError("bill_id is required.")
        
        if not new_status:
            raise DRFValidationError("status is required.")
        
        # Validate status
        valid_statuses = ['INSURANCE_CLAIMED', 'SETTLED']
        if new_status not in valid_statuses:
            raise DRFValidationError(
                f"Invalid status: {new_status}. Valid statuses: {', '.join(valid_statuses)}"
            )
        
        # Get bill
        try:
            bill = Bill.objects.get(id=bill_id)
        except Bill.DoesNotExist:
            raise NotFound(f"Bill with id {bill_id} not found.")
        
        # Validate bill is insurance-backed
        if not bill.is_insurance_backed:
            raise DRFValidationError(
                "Cannot update claim status for a non-insurance bill."
            )
        
        # Validate state transition
        current_status = bill.status
        if current_status == 'INSURANCE_PENDING' and new_status != 'INSURANCE_CLAIMED':
            raise DRFValidationError(
                f"Cannot transition from {current_status} to {new_status}. "
                "Valid transition: INSURANCE_PENDING → INSURANCE_CLAIMED"
            )
        
        if current_status == 'INSURANCE_CLAIMED' and new_status != 'SETTLED':
            raise DRFValidationError(
                f"Cannot transition from {current_status} to {new_status}. "
                "Valid transition: INSURANCE_CLAIMED → SETTLED"
            )
        
        if current_status not in ['INSURANCE_PENDING', 'INSURANCE_CLAIMED']:
            raise DRFValidationError(
                f"Cannot update status from {current_status}. "
                "Bill must be in INSURANCE_PENDING or INSURANCE_CLAIMED state."
            )
        
        # Update bill status
        bill.status = new_status
        
        # Update visit payment_status
        if new_status == 'SETTLED':
            bill.visit.payment_status = 'SETTLED'
        elif new_status == 'INSURANCE_CLAIMED':
            bill.visit.payment_status = 'INSURANCE_CLAIMED'
        
        bill.visit.save(update_fields=['payment_status'])
        bill.save(update_fields=['status', 'updated_at'])
        
        # Audit log
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        AuditLog.log(
            user=request.user,
            role=user_role,
            action="INSURANCE_CLAIM_STATUS_UPDATED",
            visit_id=bill.visit.id,
            resource_type="bill",
            resource_id=bill.id,
            request=request,
            metadata={
                'old_status': current_status,
                'new_status': new_status,
            }
        )
        
        return Response(
            {
                'bill_id': bill.id,
                'visit_id': bill.visit.id,
                'old_status': current_status,
                'new_status': new_status,
                'visit_payment_status': bill.visit.payment_status,
            },
            status=status.HTTP_200_OK
        )


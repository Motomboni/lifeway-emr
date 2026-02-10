"""
Simplified Wallet Payment API endpoints.

Endpoints:
- POST /api/wallet/topup/
- POST /api/wallet/pay/

Per EMR Rules:
- Wallet balance cannot go negative
- WalletTransaction is immutable
- Wallet payments update Bill status
- Record both WalletTransaction and BillPayment
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
from django.shortcuts import get_object_or_404
from decimal import Decimal

from apps.patients.models import Patient
from apps.visits.models import Visit
from apps.wallet.models import Wallet, WalletTransaction
from apps.billing.bill_models import Bill, BillPayment
from apps.billing.billing_service import BillingService
from core.audit import AuditLog


class WalletTopUpView(APIView):
    """
    POST /api/wallet/topup/
    
    Top up patient wallet.
    
    Payload:
    {
        "patient_id": 1,
        "amount": "10000.00",
        "description": "Wallet top-up via cash"
    }
    
    Behavior:
    - Validates patient exists
    - Gets or creates wallet
    - Credits wallet balance
    - Creates WalletTransaction (CREDIT)
    - Wallet balance cannot go negative (not applicable for credit, but validated)
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Top up wallet."""
        patient_id = request.data.get('patient_id')
        amount_str = request.data.get('amount')
        description = request.data.get('description', 'Wallet top-up')
        
        # Validate required fields
        if not patient_id:
            raise DRFValidationError("patient_id is required.")
        
        if not amount_str:
            raise DRFValidationError("amount is required.")
        
        try:
            amount = Decimal(str(amount_str))
        except (ValueError, TypeError):
            raise DRFValidationError("Invalid amount format.")
        
        if amount <= 0:
            raise DRFValidationError("Amount must be greater than zero.")
        
        # Get patient
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            raise NotFound(f"Patient with id {patient_id} not found.")
        
        # Get or create wallet
        wallet, created = Wallet.objects.get_or_create(
            patient=patient,
            defaults={
                'balance': Decimal('0.00'),
                'currency': 'NGN',
                'is_active': True
            }
        )
        
        # Credit wallet
        try:
            wallet.credit(amount, description)
        except ValidationError as e:
            raise DRFValidationError(str(e))
        
        # Get the created transaction
        transaction = WalletTransaction.objects.filter(
            wallet=wallet,
            transaction_type='CREDIT',
            amount=amount
        ).order_by('-created_at').first()
        
        # Audit log
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        AuditLog.log(
            user=request.user,
            role=user_role,
            action="WALLET_TOPUP",
            visit_id=None,
            resource_type="wallet",
            resource_id=wallet.id,
            request=request,
            metadata={
                'patient_id': patient.id,
                'amount': str(amount),
                'description': description,
            }
        )
        
        return Response(
            {
                'wallet_id': wallet.id,
                'patient_id': patient.id,
                'amount': str(amount),
                'new_balance': str(wallet.balance),
                'transaction_id': transaction.id if transaction else None,
                'description': description,
            },
            status=status.HTTP_200_OK
        )


class WalletPayView(APIView):
    """
    POST /api/wallet/pay/
    
    Pay for a visit using wallet balance.
    
    Payload:
    {
        "patient_id": 1,
        "visit_id": 1,
        "amount": "5000.00"  // Optional - defaults to outstanding balance
    }
    
    Behavior:
    - Validates patient and visit exist
    - Validates visit is OPEN
    - Validates wallet has sufficient balance
    - Debits wallet (prevents negative balance)
    - Creates WalletTransaction (DEBIT)
    - Creates BillPayment record
    - Updates Bill status
    - Records both WalletTransaction and BillPayment
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Pay for visit using wallet."""
        patient_id = request.data.get('patient_id')
        visit_id = request.data.get('visit_id')
        amount_str = request.data.get('amount')  # Optional
        
        # Validate required fields
        if not patient_id:
            raise DRFValidationError("patient_id is required.")
        
        if not visit_id:
            raise DRFValidationError("visit_id is required.")
        
        # Get patient
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            raise NotFound(f"Patient with id {patient_id} not found.")
        
        # Get visit
        try:
            visit = Visit.objects.get(id=visit_id)
        except Visit.DoesNotExist:
            raise NotFound(f"Visit with id {visit_id} not found.")
        
        # Validate visit belongs to patient
        if visit.patient.id != patient.id:
            raise DRFValidationError(
                "Visit does not belong to the specified patient."
            )
        
        # Validate visit is OPEN
        if visit.status != 'OPEN':
            raise DRFValidationError(
                f"Cannot pay for a {visit.status} visit. Visit must be OPEN."
            )
        
        # Get or create wallet
        wallet, created = Wallet.objects.get_or_create(
            patient=patient,
            defaults={
                'balance': Decimal('0.00'),
                'currency': 'NGN',
                'is_active': True
            }
        )
        
        # Get or create bill
        bill, bill_created = Bill.objects.get_or_create(visit=visit)
        
        # Calculate outstanding balance
        billing_summary = BillingService.compute_billing_summary(visit)
        outstanding_balance = billing_summary.outstanding_balance
        
        # Determine payment amount
        if amount_str:
            try:
                amount = Decimal(str(amount_str))
            except (ValueError, TypeError):
                raise DRFValidationError("Invalid amount format.")
            
            if amount <= 0:
                raise DRFValidationError("Amount must be greater than zero.")
        else:
            # Default to outstanding balance
            amount = outstanding_balance
        
        # Validate wallet has sufficient balance (prevents negative balance)
        if wallet.balance < amount:
            raise DRFValidationError(
                f"Insufficient wallet balance. Current balance: {wallet.balance}, "
                f"Requested amount: {amount}"
            )
        
        # Validate payment amount
        is_valid, error_msg = BillingService.validate_payment_amount(visit, amount)
        if not is_valid:
            raise DRFValidationError(error_msg)
        
        # Debit wallet (this prevents negative balance)
        try:
            transaction = wallet.debit(
                amount=amount,
                visit=visit,
                description=f'Payment for Visit {visit.id}',
                created_by=request.user
            )
        except ValidationError as e:
            raise DRFValidationError(str(e))
        
        # Create BillPayment record
        try:
            payment = bill.add_payment(
                amount=amount,
                payment_method='WALLET',
                transaction_reference=f'WALLET_{transaction.id}',
                notes=f'Paid from wallet. Transaction ID: {transaction.id}',
                processed_by=request.user
            )
        except ValidationError as e:
            # If payment creation fails, we need to reverse the wallet debit
            # However, since WalletTransaction is immutable, we can't delete it
            # Instead, we'll create a compensating credit transaction
            wallet.credit(
                amount,
                f'Reversal of failed payment for Visit {visit.id}'
            )
            raise DRFValidationError(f"Failed to create payment record: {str(e)}")
        
        # Recalculate billing summary
        updated_summary = BillingService.compute_billing_summary(visit)
        
        # Update visit payment_status
        visit.payment_status = updated_summary.payment_status
        visit.save(update_fields=['payment_status'])
        
        # Audit log
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        AuditLog.log(
            user=request.user,
            role=user_role,
            action="WALLET_PAYMENT",
            visit_id=visit.id,
            resource_type="wallet",
            resource_id=wallet.id,
            request=request,
            metadata={
                'patient_id': patient.id,
                'visit_id': visit.id,
                'amount': str(amount),
                'wallet_balance_before': str(wallet.balance + amount),  # Balance before debit
                'wallet_balance_after': str(wallet.balance),
                'outstanding_balance_before': str(outstanding_balance),
                'outstanding_balance_after': str(updated_summary.outstanding_balance),
                'bill_status': bill.status,
                'visit_payment_status': visit.payment_status,
            }
        )
        
        return Response(
            {
                'wallet_id': wallet.id,
                'patient_id': patient.id,
                'visit_id': visit.id,
                'bill_id': bill.id,
                'amount': str(amount),
                'wallet_balance': str(wallet.balance),
                'transaction_id': transaction.id,
                'payment_id': payment.id,
                'bill_status': bill.status,
                'outstanding_balance': str(updated_summary.outstanding_balance),
                'visit_payment_status': visit.payment_status,
            },
            status=status.HTTP_200_OK
        )


"""
Views for wallet app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from decimal import Decimal
import uuid

from .models import Wallet, WalletTransaction, PaymentChannel
from .serializers import (
    WalletSerializer,
    WalletTransactionSerializer,
    PaymentChannelSerializer,
    WalletTopUpSerializer,
    WalletPaymentSerializer,
)
from .services import PaymentGatewayService
from apps.patients.models import Patient
from apps.visits.models import Visit
from apps.billing.models import Payment
from core.audit import AuditLog


class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for wallet operations.
    
    Per EMR Rules:
    - Patients can view their own wallet
    - Receptionists can view any wallet
    - All operations are audited
    """
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Disable pagination - patients only have one wallet, receptionists may need pagination but frontend expects array
    
    def get_queryset(self):
        """Filter wallets based on user role."""
        user_role = getattr(self.request.user, 'role', None)
        
        if user_role == 'PATIENT':
            # Patients can only see their own wallet
            try:
                patient = Patient.objects.get(user=self.request.user)
                return Wallet.objects.filter(patient=patient)
            except Patient.DoesNotExist:
                return Wallet.objects.none()
        elif user_role == 'RECEPTIONIST':
            # Receptionists can see all wallets
            return Wallet.objects.all()
        else:
            # Other roles cannot access wallets
            return Wallet.objects.none()
    
    def list(self, request, *args, **kwargs):
        """
        List wallets with auto-creation for patients.
        
        For patients, ensures their Patient record and wallet exist before returning the list.
        """
        user_role = getattr(request.user, 'role', None)
        
        if user_role == 'PATIENT':
            # Ensure Patient record exists (create if missing)
            try:
                patient = Patient.objects.get(user=request.user)
                patient_created = False
            except Patient.DoesNotExist:
                # Create Patient record if it doesn't exist
                patient = Patient(
                    first_name=request.user.first_name or 'Unknown',
                    last_name=request.user.last_name or 'Patient',
                    email=request.user.email or '',
                    user=request.user,
                    is_active=True,
                    is_verified=False,
                )
                # Call clean() to generate patient_id, then save
                patient.clean()
                patient.save()
                patient_created = True
            
            # Ensure wallet exists
            wallet, wallet_created = Wallet.objects.get_or_create(
                patient=patient,
                defaults={
                    'balance': Decimal('0.00'),
                    'currency': 'NGN',
                    'is_active': True
                }
            )
            
            if patient_created or wallet_created:
                # Log creation
                user_role_str = getattr(request.user, 'role', None) or 'UNKNOWN'
                action = "PATIENT_AND_WALLET_AUTO_CREATED" if patient_created and wallet_created else \
                         ("PATIENT_AUTO_CREATED" if patient_created else "WALLET_AUTO_CREATED")
                AuditLog.log(
                    user=request.user,
                    role=user_role_str,
                    action=action,
                    resource_type="wallet",
                    resource_id=wallet.id,
                    request=request,
                    metadata={'patient_id': patient.id, 'patient_created': patient_created, 'wallet_created': wallet_created}
                )
        
        return super().list(request, *args, **kwargs)
    
    @action(detail=True, methods=['get'], url_path='transactions')
    def transactions(self, request, pk=None):
        """Get wallet transactions."""
        wallet = self.get_object()
        
        transactions = WalletTransaction.objects.filter(wallet=wallet).order_by('-created_at')
        serializer = WalletTransactionSerializer(transactions, many=True)
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='top-up')
    def top_up(self, request, pk=None):
        """
        Top up wallet using payment gateway.
        
        Creates a payment transaction and returns gateway URL.
        """
        wallet = self.get_object()
        serializer = WalletTopUpSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        amount = serializer.validated_data['amount']
        payment_channel_id = serializer.validated_data['payment_channel_id']
        description = serializer.validated_data.get('description', f'Wallet top-up: {amount}')
        callback_url = serializer.validated_data.get('callback_url')
        
        # Get payment channel
        payment_channel = get_object_or_404(PaymentChannel, id=payment_channel_id, is_active=True)
        
        # Generate unique reference
        reference = f"WALLET_{wallet.id}_{uuid.uuid4().hex[:12].upper()}"
        
        try:
            # Initialize payment with gateway
            gateway_service = PaymentGatewayService(payment_channel.channel_type)
            
            # Get patient email
            patient_email = wallet.patient.user.email if wallet.patient.user else f"patient{wallet.patient.id}@example.com"
            
            gateway_response = gateway_service.initialize_payment(
                email=patient_email,
                amount=amount,
                reference=reference,
                metadata={
                    'wallet_id': wallet.id,
                    'patient_id': wallet.patient.id,
                    'type': 'wallet_topup'
                },
                callback_url=callback_url
            )
            
            # Create pending transaction
            transaction = WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type='CREDIT',
                amount=amount,
                balance_after=wallet.balance,  # Will update after verification
                status='PENDING',
                payment_channel=payment_channel,
                gateway_transaction_id=reference,
                gateway_response=gateway_response,
                description=description,
                created_by=request.user
            )
            
            # Audit log
            user_role = getattr(request.user, 'role', None) or 'UNKNOWN'
            AuditLog.log(
                user=request.user,
                role=user_role,
                action="WALLET_TOPUP_INITIATED",
                visit_id=None,
                resource_type="wallet",
                resource_id=wallet.id,
                request=request,
                metadata={'amount': str(amount), 'reference': reference}
            )
            
            return Response({
                'transaction_id': transaction.id,
                'reference': reference,
                'authorization_url': gateway_response.get('data', {}).get('authorization_url'),
                'access_code': gateway_response.get('data', {}).get('access_code'),
            })
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], url_path='verify-payment')
    def verify_payment(self, request, pk=None):
        """
        Verify payment after gateway callback.
        
        Updates transaction status and wallet balance.
        """
        wallet = self.get_object()
        reference = request.data.get('reference')
        
        if not reference:
            return Response(
                {'error': 'Reference is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find transaction
        transaction = WalletTransaction.objects.filter(
            wallet=wallet,
            gateway_transaction_id=reference
        ).first()
        
        if not transaction:
            return Response(
                {'error': 'Transaction not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if transaction.status == 'COMPLETED':
            return Response({
                'status': 'already_verified',
                'transaction': WalletTransactionSerializer(transaction).data
            })
        
        try:
            # Verify with gateway
            gateway_service = PaymentGatewayService(transaction.payment_channel.channel_type)
            verification_response = gateway_service.verify_payment(reference)
            
            # Update transaction with gateway response
            transaction.gateway_response = verification_response
            transaction.save()
            
            # Check if payment was successful
            data = verification_response.get('data', {})
            if data.get('status') == 'success' and data.get('gateway_response') == 'Successful':
                # Credit wallet
                wallet.credit(transaction.amount, transaction.description)
                
                # Update transaction
                transaction.status = 'COMPLETED'
                transaction.balance_after = wallet.balance
                transaction.save()
                
                # Audit log
                user_role = getattr(request.user, 'role', None) or 'UNKNOWN'
                AuditLog.log(
                    user=request.user,
                    role=user_role,
                    action="WALLET_TOPUP_COMPLETED",
                    visit_id=None,
                    resource_type="wallet",
                    resource_id=wallet.id,
                    request=request,
                    metadata={'amount': str(transaction.amount), 'reference': reference}
                )
                
                return Response({
                    'status': 'success',
                    'transaction': WalletTransactionSerializer(transaction).data,
                    'wallet_balance': str(wallet.balance)
                })
            else:
                # Payment failed
                transaction.status = 'FAILED'
                transaction.save()
                
                return Response({
                    'status': 'failed',
                    'transaction': WalletTransactionSerializer(transaction).data
                })
        
        except Exception as e:
            transaction.status = 'FAILED'
            transaction.save()
            
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], url_path='pay-visit')
    def pay_visit(self, request, pk=None):
        """
        Pay for a visit using wallet balance.
        
        Per EMR Rules:
        - Wallet deductions MUST be visit-referenced
        - Wallet cannot auto-deduct without explicit billing action
        - Wallet DEBIT reduces outstanding Visit balance
        - Wallet transactions update Visit.payment_status
        - Negative wallet balances are forbidden
        
        This is an EXPLICIT billing action - no automatic deductions.
        """
        wallet = self.get_object()
        serializer = WalletPaymentSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        visit_id = serializer.validated_data['visit_id']
        amount = serializer.validated_data.get('amount')  # Optional - will calculate if not provided
        description = serializer.validated_data.get('description', f'Payment for visit {visit_id}')
        
        # Get visit
        visit = get_object_or_404(Visit, id=visit_id)
        
        # Ensure visit is OPEN
        if visit.status == 'CLOSED':
            return Response(
                {'error': 'Cannot pay for a CLOSED visit. Closed visits are immutable.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate outstanding balance using centralized BillingService
        from apps.billing.billing_service import BillingService
        
        billing_summary = BillingService.compute_billing_summary(visit)
        outstanding_balance = billing_summary.outstanding_balance
        patient_payable = billing_summary.patient_payable
        
        # If amount not provided, use outstanding balance
        if amount is None:
            amount = outstanding_balance
        
        # Validate payment amount (overpayment is allowed)
        is_valid, error_msg = BillingService.validate_payment_amount(visit, amount)
        if not is_valid:
            return Response(
                {'error': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Note: Overpayment is allowed (creates credit), so we don't restrict amount > outstanding_balance
        
        # Check if wallet has sufficient balance
        if wallet.balance < amount:
            return Response(
                {
                    'error': 'Insufficient wallet balance',
                    'wallet_balance': str(wallet.balance),
                    'required_amount': str(amount)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Debit wallet (REQUIRES visit - explicit billing action)
            transaction = wallet.debit(
                amount=amount,
                visit=visit,  # REQUIRED - visit-referenced
                description=description,
                created_by=request.user
            )
            
            # Create Payment record for visit
            payment = Payment.objects.create(
                visit=visit,
                amount=amount,
                payment_method='WALLET',
                status='CLEARED',
                transaction_reference=f'WALLET_{transaction.id}',
                notes=f'Paid from wallet. Transaction ID: {transaction.id}',
                processed_by=request.user
            )
            
            # Recalculate billing summary after payment using centralized service
            # Note: Payment record is created above, so it will be included in recalculation
            from apps.billing.billing_service import BillingService
            updated_summary = BillingService.compute_billing_summary(visit)
            
            # Update visit payment status based on billing summary
            visit.payment_status = updated_summary.payment_status
            visit.save(update_fields=['payment_status'])
            
            # Audit log
            user_role = getattr(request.user, 'role', None) or 'UNKNOWN'
            AuditLog.log(
                user=request.user,
                role=user_role,
                action="WALLET_PAYMENT_MADE",
                visit_id=visit_id,
                resource_type="wallet",
                resource_id=wallet.id,
                request=request,
                metadata={
                    'amount': str(amount),
                    'visit_id': visit_id,
                    'transaction_id': transaction.id,
                    'outstanding_balance_before': str(outstanding_balance),
                    'outstanding_balance_after': str(updated_summary.outstanding_balance),
                    'payment_status': visit.payment_status
                }
            )
            
            return Response({
                'status': 'success',
                'transaction': WalletTransactionSerializer(transaction).data,
                'payment': {
                    'id': payment.id,
                    'amount': str(payment.amount),
                    'status': payment.status
                },
                'wallet_balance': str(wallet.balance),
                'outstanding_balance': str(updated_summary.outstanding_balance),
                'visit_payment_status': visit.payment_status
            })
        
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class PaymentChannelViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for payment channels."""
    queryset = PaymentChannel.objects.filter(is_active=True)
    serializer_class = PaymentChannelSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Disable pagination - payment channels list is small

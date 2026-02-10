"""
Simplified Paystack Payment Gateway Integration.

Endpoints:
- POST /api/payments/paystack/initiate/
- POST /api/payments/paystack/webhook/

Per EMR Rules:
- Only Receptionist can initiate Paystack
- Link Paystack reference to Payment record (BillPayment)
- On webhook success:
  - Confirm payment
  - Update Bill totals
  - Generate receipt
- Prevent double payment with idempotency checks
"""
import uuid
import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import (
    PermissionDenied,
    ValidationError as DRFValidationError,
)
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal

from apps.visits.models import Visit
from apps.billing.models import PaymentIntent
from apps.billing.bill_models import Bill, BillPayment
from apps.billing.paystack_service import PaystackVisitService
from apps.billing.billing_service import BillingService
from apps.billing.receipt_service import ReceiptService
from apps.billing.permissions import CanProcessPayment
from core.audit import AuditLog


class PaystackInitiateView(APIView):
    """
    POST /api/payments/paystack/initiate/
    
    Initialize Paystack payment for a visit.
    
    Payload:
    {
        "visit_id": 1,
        "amount": "5000.00",
        "callback_url": "https://example.com/callback"  // Optional
    }
    
    Rules:
    - Only Receptionist can initiate
    - Visit must be OPEN
    - Visit must not be insurance-backed (insurance bills cannot accept Paystack)
    - System generates Paystack reference
    - Returns authorization_url for frontend redirect
    """
    permission_classes = [IsAuthenticated, CanProcessPayment]
    
    def post(self, request):
        """Initialize Paystack payment."""
        visit_id = request.data.get('visit_id')
        amount_str = request.data.get('amount')
        callback_url = request.data.get('callback_url')
        
        # Validate required fields
        if not visit_id:
            raise DRFValidationError("visit_id is required.")
        
        if not amount_str:
            raise DRFValidationError("amount is required.")
        
        try:
            amount = Decimal(str(amount_str))
        except (ValueError, TypeError):
            raise DRFValidationError("Invalid amount format.")
        
        if amount <= 0:
            raise DRFValidationError("Amount must be greater than zero.")
        
        # Get visit
        try:
            visit = Visit.objects.get(id=visit_id)
        except Visit.DoesNotExist:
            raise DRFValidationError(f"Visit with id {visit_id} not found.")
        
        # Validate visit is OPEN
        if visit.status != 'OPEN':
            raise DRFValidationError(
                f"Cannot initiate payment for a {visit.status} visit. Visit must be OPEN."
            )
        
        # Get or create bill
        bill, created = Bill.objects.get_or_create(visit=visit)
        
        # Validate bill is not insurance-backed (insurance bills cannot accept Paystack)
        if bill.is_insurance_backed:
            raise DRFValidationError(
                "Insurance-backed bills cannot accept Paystack payments. "
                "Please use insurance claim submission instead."
            )
        
        # Calculate outstanding balance
        billing_summary = BillingService.compute_billing_summary(visit)
        outstanding_balance = billing_summary.outstanding_balance
        
        # Validate payment amount
        is_valid, error_msg = BillingService.validate_payment_amount(visit, amount)
        if not is_valid:
            raise DRFValidationError(error_msg)
        
        # Generate unique Paystack reference
        paystack_reference = f"VISIT-{visit.id}-{uuid.uuid4().hex[:12].upper()}"
        
        # Initialize Paystack transaction
        paystack_service = PaystackVisitService()
        
        try:
            # Get patient email (generic, not PHI)
            customer_email = None
            if visit.patient.user:
                customer_email = visit.patient.user.email
            
            paystack_response = paystack_service.initialize_transaction(
                visit_id=visit.id,
                amount=amount,
                reference=paystack_reference,
                callback_url=callback_url,
                customer_email=customer_email
            )
        except Exception as e:
            raise DRFValidationError(f"Paystack initialization failed: {str(e)}")
        
        # Create PaymentIntent
        payment_intent = PaymentIntent.objects.create(
            visit=visit,
            paystack_reference=paystack_reference,
            amount=amount,
            status='INITIALIZED',
            paystack_authorization_url=paystack_response.get('data', {}).get('authorization_url'),
            paystack_access_code=paystack_response.get('data', {}).get('access_code'),
            created_by=request.user
        )
        
        # Audit log
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        AuditLog.log(
            user=request.user,
            role=user_role,
            action="PAYSTACK_PAYMENT_INITIATED",
            visit_id=visit.id,
            resource_type="payment_intent",
            resource_id=payment_intent.id,
            request=request,
            metadata={
                'amount': str(amount),
                'reference': paystack_reference,
                'outstanding_balance': str(outstanding_balance),
            }
        )
        
        return Response(
            {
                'payment_intent_id': payment_intent.id,
                'reference': paystack_reference,
                'authorization_url': paystack_response.get('data', {}).get('authorization_url'),
                'access_code': paystack_response.get('data', {}).get('access_code'),
                'amount': str(amount),
                'visit_id': visit.id,
            },
            status=status.HTTP_201_CREATED
        )


@csrf_exempt
def paystack_webhook_view(request):
    """
    POST /api/payments/paystack/webhook/
    
    Paystack webhook handler - idempotent and secure.
    
    Security Rules:
    1. Webhook signature MUST be verified
    2. Idempotent processing (can be called multiple times safely)
    3. Server-side verification only
    4. No PHI in processing
    5. Audit logging
    
    On Success:
    - Confirm payment
    - Update Bill totals
    - Generate receipt
    
    Webhook payload structure:
    {
        "event": "charge.success",
        "data": {
            "reference": "VISIT-123-ABC123",
            "status": "success",
            ...
        }
    }
    """
    if request.method != 'POST':
        return JsonResponse(
            {'error': 'Method not allowed'},
            status=405
        )
    
    # Get webhook signature
    signature = request.headers.get('X-Paystack-Signature', '')
    
    if not signature:
        return JsonResponse(
            {'error': 'Missing X-Paystack-Signature header'},
            status=400
        )
    
    # Get raw request body
    payload = request.body
    
    # Verify webhook signature
    paystack_service = PaystackVisitService()
    
    if not paystack_service.verify_webhook_signature(payload, signature):
        return JsonResponse(
            {'error': 'Invalid webhook signature'},
            status=401
        )
    
    # Parse webhook payload
    try:
        webhook_data = json.loads(payload.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse(
            {'error': 'Invalid JSON payload'},
            status=400
        )
    
    event = webhook_data.get('event')
    data = webhook_data.get('data', {})
    reference = data.get('reference')
    
    if not reference:
        return JsonResponse(
            {'error': 'Missing reference in webhook data'},
            status=400
        )
    
    # Only process charge.success events
    if event != 'charge.success':
        return JsonResponse(
            {'message': f'Event {event} not processed'},
            status=200
        )
    
    # Find PaymentIntent by reference
    try:
        payment_intent = PaymentIntent.objects.select_related('visit').get(
            paystack_reference=reference
        )
    except PaymentIntent.DoesNotExist:
        return JsonResponse(
            {'error': f'PaymentIntent not found for reference: {reference}'},
            status=404
        )
    
    # Idempotency check: If already verified, return success
    if payment_intent.is_verified():
        # Get existing payment
        bill_payment = None
        if payment_intent.payment:
            # Try to find BillPayment linked to this Payment
            try:
                bill_payment = BillPayment.objects.get(
                    transaction_reference=payment_intent.paystack_reference
                )
            except BillPayment.DoesNotExist:
                pass
        
        return JsonResponse(
            {
                'message': 'Payment already verified (idempotent)',
                'payment_intent_id': payment_intent.id,
                'payment_id': payment_intent.payment.id if payment_intent.payment else None,
                'bill_payment_id': bill_payment.id if bill_payment else None,
            },
            status=200
        )
    
    # Verify transaction server-side (do not trust webhook data alone)
    try:
        paystack_response = paystack_service.verify_transaction(reference)
    except Exception as e:
        payment_intent.mark_as_failed(reason=f"Webhook verification failed: {str(e)}")
        return JsonResponse(
            {'error': f'Paystack verification failed: {str(e)}'},
            status=500
        )
    
    # Check if transaction is successful
    if not paystack_service.is_transaction_successful(paystack_response):
        payment_intent.mark_as_failed(reason="Transaction not successful")
        return JsonResponse(
            {'error': 'Transaction not successful'},
            status=400
        )
    
    # Verify visit_id in metadata matches (security check)
    metadata_visit_id = paystack_service.extract_visit_id_from_metadata(paystack_response)
    if metadata_visit_id != payment_intent.visit_id:
        payment_intent.mark_as_failed(reason="Visit ID mismatch in Paystack metadata")
        return JsonResponse(
            {'error': 'Security check failed: Visit ID mismatch'},
            status=400
        )
    
    # Get visit and bill
    visit = payment_intent.visit
    bill, created = Bill.objects.get_or_create(visit=visit)
    
    # Validate bill is not insurance-backed
    if bill.is_insurance_backed:
        payment_intent.mark_as_failed(reason="Cannot process Paystack payment for insurance-backed bill")
        return JsonResponse(
            {'error': 'Cannot process Paystack payment for insurance-backed bill'},
            status=400
        )
    
    # Mark PaymentIntent as verified
    try:
        payment_intent.status = 'VERIFIED'
        payment_intent.verified_at = timezone.now()
        
        # Store Paystack transaction details
        if 'data' in paystack_response:
            data = paystack_response['data']
            payment_intent.paystack_transaction_id = data.get('id', '')
            if 'customer' in data:
                payment_intent.paystack_customer_email = data['customer'].get('email', '')
        
        payment_intent.save()
    except Exception as e:
        return JsonResponse(
            {'error': f'Failed to update payment intent: {str(e)}'},
            status=500
        )
    
    # Create BillPayment record (idempotency: check if already exists)
    bill_payment, payment_created = BillPayment.objects.get_or_create(
        transaction_reference=payment_intent.paystack_reference,
        defaults={
            'bill': bill,
            'amount': payment_intent.amount,
            'payment_method': 'PAYSTACK',
            'notes': f"Paystack payment verified. Transaction ID: {payment_intent.paystack_transaction_id}",
            'processed_by': payment_intent.created_by,
        }
    )
    
    # If payment already exists, return success (idempotency)
    if not payment_created:
        return JsonResponse(
            {
                'message': 'Payment already processed (idempotent)',
                'payment_intent_id': payment_intent.id,
                'bill_payment_id': bill_payment.id,
            },
            status=200
        )
    
    # Update Bill totals
    bill.recalculate_totals()
    bill.save(update_fields=['total_amount', 'amount_paid', 'outstanding_balance', 'status', 'updated_at'])
    
    # Update Visit payment_status
    billing_summary = BillingService.compute_billing_summary(visit)
    visit.payment_status = billing_summary.payment_status
    visit.save(update_fields=['payment_status'])
    
    # Generate receipt
    try:
        receipt_data = ReceiptService.generate_receipt(visit)
    except Exception as e:
        # Log error but don't fail the webhook
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to generate receipt for visit {visit.id}: {str(e)}")
        receipt_data = None
    
    # Audit log (webhook processing)
    AuditLog.log(
        user=None,  # System action
        role='SYSTEM',
        action="PAYSTACK_WEBHOOK_PROCESSED",
        visit_id=visit.id,
        resource_type="payment_intent",
        resource_id=payment_intent.id,
        request=request,
        metadata={
            'reference': reference,
            'amount': str(payment_intent.amount),
            'bill_payment_id': bill_payment.id,
            'bill_status': bill.status,
            'visit_payment_status': visit.payment_status,
        }
    )
    
    return JsonResponse(
        {
            'message': 'Webhook processed successfully',
            'payment_intent_id': payment_intent.id,
            'bill_payment_id': bill_payment.id,
            'bill_status': bill.status,
            'visit_payment_status': visit.payment_status,
            'receipt_number': receipt_data.get('receipt_number') if receipt_data else None,
        },
        status=200
    )


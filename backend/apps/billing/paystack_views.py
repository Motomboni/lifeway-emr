"""
Paystack payment views for Visit billing.

Per EMR Rules:
- Paystack transactions MUST be visit-scoped
- Receptionist-only access for initialization
- Server-side verification only
- Webhook handler with idempotency
- No PHI exposure
"""
import uuid
import json
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import (
    PermissionDenied,
    ValidationError as DRFValidationError,
)
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

from .models import PaymentIntent, Payment
from .serializers import (
    PaymentIntentSerializer,
    PaymentIntentCreateSerializer,
    PaymentIntentVerifySerializer,
)
from .paystack_service import PaystackVisitService
from .permissions import CanProcessPayment
from apps.visits.models import Visit
from core.permissions import IsVisitOpen
from core.audit import AuditLog


class PaymentIntentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for PaymentIntent - Paystack payment processing.
    
    Endpoint: /api/v1/visits/{visit_id}/payment-intents/
    
    Rules enforced:
    - Visit-scoped architecture
    - Receptionist-only initialization
    - Server-side verification only
    - Audit logging
    """
    
    serializer_class = PaymentIntentSerializer
    permission_classes = [CanProcessPayment, IsVisitOpen]
    
    def get_queryset(self):
        """Get payment intents for the specific visit."""
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            return PaymentIntent.objects.none()
        
        return PaymentIntent.objects.filter(visit_id=visit_id).select_related(
            'visit',
            'created_by',
            'payment'
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
                detail="Only Receptionists can process Paystack payments.",
                code='role_forbidden'
            )
    
    @action(detail=False, methods=['post'], url_path='initialize')
    def initialize(self, request, visit_id=None):
        """
        Initialize Paystack payment for a Visit.
        
        POST /api/v1/visits/{visit_id}/payment-intents/initialize/
        
        Rules:
        1. Only Receptionist can initialize
        2. Visit must be OPEN
        3. System generates Paystack reference
        4. No PHI sent to Paystack
        5. Audit log created
        """
        visit = self.get_visit()
        
        # Enforce user role
        self.check_user_role(request)
        
        # Validate request data
        serializer = PaymentIntentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Ensure visit_id in URL matches request data
        if serializer.validated_data['visit_id'] != visit.id:
            raise DRFValidationError(
                "visit_id in URL must match visit_id in request data."
            )
        
        amount = serializer.validated_data['amount']
        callback_url = serializer.validated_data.get('callback_url')
        customer_email = serializer.validated_data.get('customer_email')
        
        # Generate unique Paystack reference
        # Format: VISIT-{visit_id}-{uuid}
        paystack_reference = f"VISIT-{visit.id}-{uuid.uuid4().hex[:12].upper()}"
        
        # Initialize Paystack transaction
        paystack_service = PaystackVisitService()
        
        try:
            paystack_response = paystack_service.initialize_transaction(
                visit_id=visit.id,
                amount=amount,
                reference=paystack_reference,
                callback_url=callback_url,
                customer_email=customer_email
            )
        except Exception as e:
            return Response(
                {'error': f'Paystack initialization failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
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
            action="PAYSTACK_PAYMENT_INITIALIZED",
            visit_id=visit.id,
            resource_type="payment_intent",
            resource_id=payment_intent.id,
            request=request
        )
        
        return Response(
            {
                'payment_intent': PaymentIntentSerializer(payment_intent).data,
                'authorization_url': paystack_response.get('data', {}).get('authorization_url'),
                'access_code': paystack_response.get('data', {}).get('access_code'),
                'public_key': paystack_service.public_key,  # For frontend Paystack.js
            },
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'], url_path='verify')
    def verify(self, request, visit_id=None, pk=None):
        """
        Verify Paystack payment (server-side only).
        
        POST /api/v1/visits/{visit_id}/payment-intents/{id}/verify/
        
        Rules:
        1. Only Receptionist can trigger verification
        2. Server-side Paystack verification (frontend NOT trusted)
        3. Payment record created after verification
        4. Idempotent (can be called multiple times safely)
        5. Audit log created
        """
        visit = self.get_visit()
        payment_intent = self.get_object()
        
        # Enforce user role
        self.check_user_role(request)
        
        # Validate payment intent belongs to visit
        if payment_intent.visit_id != visit.id:
            raise DRFValidationError(
                "Payment intent does not belong to this visit."
            )
        
        # Validate request data
        serializer = PaymentIntentVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        reference = serializer.validated_data['reference']
        
        # Ensure reference matches
        if reference != payment_intent.paystack_reference:
            raise DRFValidationError(
                "Reference does not match payment intent."
            )
        
        # If already verified, return existing payment (idempotency)
        if payment_intent.is_verified():
            return Response(
                {
                    'message': 'Payment already verified.',
                    'payment_intent': PaymentIntentSerializer(payment_intent).data,
                    'payment': payment_intent.payment.id if payment_intent.payment else None,
                },
                status=status.HTTP_200_OK
            )
        
        # Server-side verification (CRITICAL: Do not trust frontend)
        paystack_service = PaystackVisitService()
        
        try:
            paystack_response = paystack_service.verify_transaction(reference)
        except Exception as e:
            payment_intent.mark_as_failed(reason=str(e))
            return Response(
                {'error': f'Paystack verification failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if transaction is successful
        if not paystack_service.is_transaction_successful(paystack_response):
            payment_intent.mark_as_failed(reason="Transaction not successful")
            return Response(
                {
                    'error': 'Payment verification failed. Transaction not successful.',
                    'paystack_response': paystack_response
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify visit_id in metadata matches (security check)
        metadata_visit_id = paystack_service.extract_visit_id_from_metadata(paystack_response)
        if metadata_visit_id != visit.id:
            payment_intent.mark_as_failed(reason="Visit ID mismatch in Paystack metadata")
            return Response(
                {'error': 'Security check failed: Visit ID mismatch.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Mark as verified and create Payment record
        try:
            payment = payment_intent.mark_as_verified(paystack_response)
        except Exception as e:
            return Response(
                {'error': f'Failed to create payment record: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Audit log
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        AuditLog.log(
            user=request.user,
            role=user_role,
            action="PAYSTACK_PAYMENT_VERIFIED",
            visit_id=visit.id,
            resource_type="payment_intent",
            resource_id=payment_intent.id,
            request=request
        )
        
        return Response(
            {
                'message': 'Payment verified successfully.',
                'payment_intent': PaymentIntentSerializer(payment_intent).data,
                'payment_id': payment.id if payment else None,
            },
            status=status.HTTP_200_OK
        )
    
    def list(self, request, *args, **kwargs):
        """List payment intents for visit."""
        visit = self.get_visit()
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve payment intent."""
        payment_intent = self.get_object()
        serializer = self.get_serializer(payment_intent)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """Disable direct creation - use initialize action instead."""
        raise PermissionDenied(
            detail="Use /initialize/ endpoint to create payment intents.",
            code='use_initialize_endpoint'
        )
    
    def update(self, request, *args, **kwargs):
        """Disable updates - payment intents are immutable after creation."""
        raise PermissionDenied(
            detail="Payment intents cannot be modified after creation.",
            code='immutable_payment_intent'
        )
    
    def destroy(self, request, *args, **kwargs):
        """Disable deletion - payment intents are immutable."""
        raise PermissionDenied(
            detail="Payment intents cannot be deleted.",
            code='immutable_payment_intent'
        )


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])  # Webhook must be accessible without auth
def paystack_webhook(request):
    """
    Paystack webhook handler - idempotent and secure.
    
    POST /api/v1/billing/paystack/webhook/
    
    Security Rules:
    1. Webhook signature MUST be verified
    2. Idempotent processing (can be called multiple times safely)
    3. Server-side verification only
    4. No PHI in processing
    5. Audit logging
    
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
        payment_intent = PaymentIntent.objects.get(paystack_reference=reference)
    except PaymentIntent.DoesNotExist:
        return JsonResponse(
            {'error': f'PaymentIntent not found for reference: {reference}'},
            status=404
        )
    
    # Idempotency check: If already verified, return success
    if payment_intent.is_verified():
        return JsonResponse(
            {
                'message': 'Payment already verified (idempotent)',
                'payment_intent_id': payment_intent.id,
                'payment_id': payment_intent.payment.id if payment_intent.payment else None
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
    
    # Mark as verified and create Payment record
    try:
        payment = payment_intent.mark_as_verified(paystack_response)
    except Exception as e:
        return JsonResponse(
            {'error': f'Failed to create payment record: {str(e)}'},
            status=500
        )
    
    # Audit log (webhook processing)
    AuditLog.log(
        user=None,  # System action
        role='SYSTEM',
        action="PAYSTACK_WEBHOOK_PROCESSED",
        visit_id=payment_intent.visit_id,
        resource_type="payment_intent",
        resource_id=payment_intent.id,
        request=request
    )
    
    return JsonResponse(
        {
            'message': 'Webhook processed successfully',
            'payment_intent_id': payment_intent.id,
            'payment_id': payment.id if payment else None
        },
        status=200
    )


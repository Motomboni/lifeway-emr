"""
Payment serializers - visit-scoped payment processing.

Per EMR Rules:
- Receptionist: Can process payments
- Payment is visit-scoped
- All payment actions are audited
"""
from rest_framework import serializers
from .models import Payment, PaymentIntent


class PaymentSerializer(serializers.ModelSerializer):
    """
    Base serializer for Payment.
    """
    
    visit_id = serializers.IntegerField(source='visit.id', read_only=True)
    processed_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = [
            'id',
            'visit',
            'visit_id',
            'amount',
            'payment_method',
            'status',
            'transaction_reference',
            'notes',
            'processed_by',
            'processed_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'visit_id',
            'processed_by',
            'processed_by_name',
            'created_at',
            'updated_at',
        ]
    
    def get_processed_by_name(self, obj):
        """Get processor's full name."""
        if obj.processed_by:
            return f"{obj.processed_by.first_name} {obj.processed_by.last_name}"
        return None


class PaymentCreateSerializer(PaymentSerializer):
    """
    Serializer for creating payments (Receptionist only).
    
    Receptionist provides:
    - visit (optional - visit ID, can be provided in URL context)
    - amount (required)
    - payment_method (required)
    - transaction_reference (optional)
    - notes (optional)
    
    System sets:
    - status (defaults to PENDING, can be set to CLEARED)
    - processed_by (from authenticated user)
    
    Note: When used in visit-scoped endpoints, visit is provided from URL context.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set queryset dynamically to avoid circular import
        from apps.visits.models import Visit
        # Make visit optional - it can come from URL context in visit-scoped endpoints
        self.fields['visit'] = serializers.PrimaryKeyRelatedField(
            queryset=Visit.objects.filter(status='OPEN'),
            required=False,  # Optional - can be provided from URL context
            help_text="Visit ID for this payment (optional if provided in URL)"
        )
    
    def validate_visit(self, value):
        """Ensure visit is OPEN if provided."""
        if value and value.status == 'CLOSED':
            raise serializers.ValidationError(
                "Cannot process payment for a CLOSED visit. Closed visits are immutable."
            )
        return value
    
    def validate_amount(self, value):
        """Ensure amount is positive."""
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be greater than zero.")
        return value
    
    def validate(self, attrs):
        """Validate payment data and check for duplicates."""
        # Check for duplicate payment (only on create, not update)
        if self.instance is None:
            from core.duplicate_prevention import check_payment_duplicate
            from django.core.exceptions import ValidationError as DjangoValidationError
            
            visit = attrs.get('visit') or self.context.get('visit')
            amount = attrs.get('amount')
            payment_method = attrs.get('payment_method')
            
            if visit and amount and payment_method:
                try:
                    check_payment_duplicate(
                        visit=visit,
                        amount=amount,
                        payment_method=payment_method,
                        window_minutes=2
                    )
                except DjangoValidationError as e:
                    raise serializers.ValidationError(str(e))
        
        return attrs


class PaymentClearSerializer(serializers.Serializer):
    """
    Serializer for clearing a payment.
    
    Receptionist provides:
    - transaction_reference (optional)
    - notes (optional)
    """
    
    transaction_reference = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class PaymentIntentSerializer(serializers.ModelSerializer):
    """
    Serializer for PaymentIntent (read-only for most fields).
    """
    
    visit_id = serializers.IntegerField(source='visit.id', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    payment_id = serializers.IntegerField(source='payment.id', read_only=True)
    
    class Meta:
        model = PaymentIntent
        fields = [
            'id',
            'visit',
            'visit_id',
            'paystack_reference',
            'amount',
            'status',
            'paystack_authorization_url',
            'paystack_access_code',
            'paystack_transaction_id',
            'verified_at',
            'payment',
            'payment_id',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'visit_id',
            'paystack_reference',
            'status',
            'paystack_authorization_url',
            'paystack_access_code',
            'paystack_transaction_id',
            'verified_at',
            'payment',
            'payment_id',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
    
    def get_created_by_name(self, obj):
        """Get creator's full name."""
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}"
        return None


class PaymentIntentCreateSerializer(serializers.Serializer):
    """
    Serializer for creating PaymentIntent (Paystack initialization).
    
    Receptionist provides:
    - visit_id (required)
    - amount (required)
    - callback_url (optional)
    - customer_email (optional - generic, not PHI)
    
    System generates:
    - paystack_reference (unique)
    - Paystack transaction initialization
    """
    
    visit_id = serializers.IntegerField(required=True)
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=True
    )
    callback_url = serializers.URLField(required=False, allow_null=True)
    customer_email = serializers.EmailField(required=False, allow_null=True)
    
    def validate_visit_id(self, value):
        """Ensure visit exists and is OPEN."""
        from apps.visits.models import Visit
        try:
            visit = Visit.objects.get(pk=value)
            if visit.status == 'CLOSED':
                raise serializers.ValidationError(
                    "Cannot create payment intent for a CLOSED visit."
                )
            return value
        except Visit.DoesNotExist:
            raise serializers.ValidationError("Visit does not exist.")
    
    def validate_amount(self, value):
        """Ensure amount is positive."""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value


class PaymentIntentVerifySerializer(serializers.Serializer):
    """
    Serializer for verifying PaymentIntent (server-side only).
    
    Receptionist provides:
    - reference (required) - Paystack transaction reference
    
    System performs:
    - Server-side Paystack verification
    - Payment record creation
    """
    
    reference = serializers.CharField(required=True, max_length=255)

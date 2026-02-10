"""
Serializers for BillingLineItem model.
"""
from rest_framework import serializers
from decimal import Decimal

from .billing_line_item_models import BillingLineItem
from apps.visits.models import Visit
from apps.consultations.models import Consultation
from .service_catalog_models import ServiceCatalog


class BillingLineItemSerializer(serializers.ModelSerializer):
    """
    Serializer for BillingLineItem model.
    
    Includes read-only fields for related objects.
    """
    service_catalog_code = serializers.CharField(
        source='service_catalog.service_code',
        read_only=True,
        help_text="Current service code from ServiceCatalog"
    )
    
    service_catalog_name = serializers.CharField(
        source='service_catalog.name',
        read_only=True,
        help_text="Current service name from ServiceCatalog"
    )
    
    visit_id = serializers.IntegerField(
        source='visit.id',
        read_only=True,
        help_text="Visit ID"
    )
    
    patient_name = serializers.CharField(
        source='visit.patient.get_full_name',
        read_only=True,
        help_text="Patient name"
    )
    
    consultation_id = serializers.IntegerField(
        source='consultation.id',
        read_only=True,
        allow_null=True,
        help_text="Consultation ID (if linked)"
    )
    
    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True,
        allow_null=True,
        help_text="Name of user who created this item"
    )
    
    class Meta:
        model = BillingLineItem
        fields = [
            'id',
            'service_catalog',
            'service_catalog_code',
            'service_catalog_name',
            'visit',
            'visit_id',
            'patient_name',
            'consultation',
            'consultation_id',
            'source_service_code',
            'source_service_name',
            'amount',
            'bill_status',
            'amount_paid',
            'outstanding_amount',
            'payment_method',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
            'paid_at',
        ]
        read_only_fields = [
            'id',
            'source_service_code',
            'source_service_name',
            'outstanding_amount',
            'bill_status',
            'paid_at',
            'created_at',
            'updated_at',
        ]


class BillingLineItemCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating BillingLineItem from ServiceCatalog.
    
    Automatically snapshots service details and calculates amounts.
    """
    service_catalog_id = serializers.IntegerField(
        write_only=True,
        help_text="ServiceCatalog ID to create billing line item from"
    )
    
    visit_id = serializers.IntegerField(
        write_only=True,
        help_text="Visit ID this billing line item belongs to"
    )
    
    consultation_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        write_only=True,
        help_text="Consultation ID (optional, for consultation services)"
    )
    
    class Meta:
        model = BillingLineItem
        fields = [
            'service_catalog_id',
            'visit_id',
            'consultation_id',
        ]
    
    def validate_service_catalog_id(self, value):
        """Validate service catalog exists and is active."""
        try:
            service = ServiceCatalog.objects.get(pk=value)
            if not service.is_active:
                raise serializers.ValidationError(
                    f"ServiceCatalog '{service.service_code}' is not active."
                )
            return value
        except ServiceCatalog.DoesNotExist:
            raise serializers.ValidationError(f"ServiceCatalog with ID {value} does not exist.")
    
    def validate_visit_id(self, value):
        """Validate visit exists and is open."""
        try:
            visit = Visit.objects.get(pk=value)
            if visit.status == 'CLOSED':
                raise serializers.ValidationError(
                    "Cannot create billing line items for a CLOSED visit."
                )
            return value
        except Visit.DoesNotExist:
            raise serializers.ValidationError(f"Visit with ID {value} does not exist.")
    
    def validate_consultation_id(self, value):
        """Validate consultation exists and belongs to the visit."""
        if value is None:
            return value
        
        try:
            consultation = Consultation.objects.get(pk=value)
            # Will validate visit relationship in validate()
            return value
        except Consultation.DoesNotExist:
            raise serializers.ValidationError(f"Consultation with ID {value} does not exist.")
    
    def validate(self, attrs):
        """Cross-field validation."""
        service_catalog_id = attrs.get('service_catalog_id')
        visit_id = attrs.get('visit_id')
        consultation_id = attrs.get('consultation_id')
        
        # Get objects for validation
        service = ServiceCatalog.objects.get(pk=service_catalog_id)
        visit = Visit.objects.get(pk=visit_id)
        
        # Check if billing line item already exists for this service and visit
        existing = BillingLineItem.objects.filter(
            service_catalog=service,
            visit=visit
        ).first()
        
        if existing:
            raise serializers.ValidationError(
                f"Billing line item already exists for service '{service.service_code}' "
                f"and visit {visit_id}. Each service can only create one billing line item per visit."
            )
        
        # Validate consultation relationship
        if consultation_id:
            consultation = Consultation.objects.get(pk=consultation_id)
            
            # Consultation must belong to the same visit
            if consultation.visit != visit:
                raise serializers.ValidationError(
                    "Consultation must belong to the same visit."
                )
            
            # Service must be a consultation service
            if service.workflow_type != 'GOPD_CONSULT':
                raise serializers.ValidationError(
                    "Consultation can only be linked to GOPD_CONSULT services."
                )
        
        return attrs
    
    def create(self, validated_data):
        """Create billing line item with snapshot of service details."""
        service_catalog_id = validated_data.pop('service_catalog_id')
        visit_id = validated_data.pop('visit_id')
        consultation_id = validated_data.pop('consultation_id', None)
        
        # Get objects
        service = ServiceCatalog.objects.get(pk=service_catalog_id)
        visit = Visit.objects.get(pk=visit_id)
        consultation = Consultation.objects.get(pk=consultation_id) if consultation_id else None
        
        # Create billing line item with snapshot
        billing_line_item = BillingLineItem.objects.create(
            service_catalog=service,
            visit=visit,
            consultation=consultation,
            source_service_code=service.service_code,
            source_service_name=service.name,
            amount=service.amount,  # Snapshot amount
            created_by=self.context['request'].user if self.context.get('request') else None,
        )
        
        return billing_line_item


class BillingLineItemUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating BillingLineItem.
    
    Only allows updating payment-related fields.
    Immutable fields (amount, service_catalog, visit) cannot be modified.
    """
    class Meta:
        model = BillingLineItem
        fields = [
            'amount_paid',
            'payment_method',
        ]
    
    def validate_amount_paid(self, value):
        """Validate amount_paid."""
        if value < 0:
            raise serializers.ValidationError("Amount paid cannot be negative.")
        
        # Check if item is already paid
        if self.instance and self.instance.is_immutable():
            raise serializers.ValidationError(
                "Cannot modify payment for a PAID billing line item."
            )
        
        if value > self.instance.amount:
            raise serializers.ValidationError(
                f"Amount paid ({value}) cannot exceed billing amount ({self.instance.amount})."
            )
        
        return value
    
    def update(self, instance, validated_data):
        """Update billing line item payment."""
        # Use the model's apply_payment method if amount_paid is being updated
        if 'amount_paid' in validated_data:
            new_amount_paid = validated_data['amount_paid']
            payment_method = validated_data.get('payment_method', 'CASH')
            
            # Calculate payment difference
            payment_difference = new_amount_paid - instance.amount_paid
            
            if payment_difference > 0:
                # Apply payment
                instance.apply_payment(payment_difference, payment_method)
            elif payment_difference < 0:
                # Refund (not typically allowed, but handle gracefully)
                raise serializers.ValidationError(
                    "Cannot reduce amount paid. Refunds must be processed separately."
                )
        else:
            # Just update payment_method
            instance.payment_method = validated_data.get('payment_method', instance.payment_method)
            instance.save()
        
        return instance


class BillingLineItemPaymentSerializer(serializers.Serializer):
    """
    Serializer for applying payment to a BillingLineItem.
    """
    payment_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Payment amount to apply"
    )
    
    payment_method = serializers.ChoiceField(
        choices=BillingLineItem.PAYMENT_METHOD_CHOICES,
        help_text="Payment method (CASH, WALLET, HMO, PAYSTACK)"
    )
    
    def validate_payment_amount(self, value):
        """Validate payment amount."""
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be greater than zero.")
        return value
    
    def validate(self, attrs):
        """Validate payment against billing line item."""
        instance = self.context.get('instance')
        if not instance:
            raise serializers.ValidationError("Billing line item instance is required.")
        
        payment_amount = attrs['payment_amount']
        
        if instance.is_immutable():
            raise serializers.ValidationError(
                "Cannot apply payment to a PAID billing line item."
            )
        
        if payment_amount > instance.outstanding_amount:
            raise serializers.ValidationError(
                f"Payment amount ({payment_amount}) exceeds outstanding amount "
                f"({instance.outstanding_amount})."
            )
        
        return attrs
    
    def save(self):
        """Apply payment to billing line item."""
        instance = self.context['instance']
        payment_amount = self.validated_data['payment_amount']
        payment_method = self.validated_data['payment_method']
        
        instance.apply_payment(payment_amount, payment_method)
        
        return instance


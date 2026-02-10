"""
Insurance serializers - visit-scoped insurance management.

Per EMR Rules:
- Receptionist-only access
- Visit-scoped insurance data
- Insurance alters payment responsibility, does NOT bypass billing
"""
from rest_framework import serializers
from .insurance_models import HMOProvider, VisitInsurance


class HMOProviderSerializer(serializers.ModelSerializer):
    """
    Serializer for HMO Provider.
    """
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = HMOProvider
        fields = [
            'id',
            'name',
            'code',
            'contact_person',
            'contact_phone',
            'contact_email',
            'address',
            'is_active',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]


class HMOProviderCreateSerializer(HMOProviderSerializer):
    """
    Serializer for creating HMO Provider (Receptionist only).
    """
    
    def validate_name(self, value):
        """Ensure provider name is unique."""
        if HMOProvider.objects.filter(name__iexact=value.strip()).exists():
            raise serializers.ValidationError("An HMO provider with this name already exists.")
        return value.strip()
    
    def validate_code(self, value):
        """Ensure provider code is unique if provided."""
        if value:
            value = value.strip()
            if HMOProvider.objects.filter(code=value).exists():
                raise serializers.ValidationError("An HMO provider with this code already exists.")
        return value


class VisitInsuranceSerializer(serializers.ModelSerializer):
    """
    Serializer for Visit Insurance.
    """
    visit_id = serializers.IntegerField(source='visit.id', read_only=True)
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    # Computed fields
    patient_payable = serializers.SerializerMethodField()
    insurance_amount = serializers.SerializerMethodField()
    is_fully_covered = serializers.SerializerMethodField()
    
    class Meta:
        model = VisitInsurance
        fields = [
            'id',
            'visit',
            'visit_id',
            'provider',
            'provider_name',
            'policy_number',
            'coverage_type',
            'coverage_percentage',
            'approval_status',
            'approved_amount',
            'approval_reference',
            'approval_date',
            'rejection_reason',
            'notes',
            'patient_payable',
            'insurance_amount',
            'is_fully_covered',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'visit_id',
            'provider_name',
            'patient_payable',
            'insurance_amount',
            'is_fully_covered',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
    
    def get_patient_payable(self, obj):
        """Compute patient payable amount using centralized BillingService."""
        from .billing_service import BillingService
        
        summary = BillingService.compute_billing_summary(obj.visit)
        return str(summary.patient_payable)
    
    def get_insurance_amount(self, obj):
        """Compute insurance-covered amount using centralized BillingService."""
        from .billing_service import BillingService
        
        summary = BillingService.compute_billing_summary(obj.visit)
        return str(summary.insurance_amount)
    
    def get_is_fully_covered(self, obj):
        """Check if patient is fully covered using centralized BillingService."""
        from .billing_service import BillingService
        
        summary = BillingService.compute_billing_summary(obj.visit)
        return summary.is_fully_covered_by_insurance


class VisitInsuranceCreateSerializer(VisitInsuranceSerializer):
    """
    Serializer for creating Visit Insurance (Receptionist only).
    
    Receptionist provides:
    - visit (required - visit ID)
    - provider (required - HMO Provider ID)
    - policy_number (required)
    - coverage_type (required: FULL or PARTIAL)
    - coverage_percentage (required for PARTIAL, defaults to 100 for FULL)
    - notes (optional)
    
    System sets:
    - approval_status (defaults to PENDING)
    - created_by (from authenticated user)
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set queryset dynamically to avoid circular import
        from apps.visits.models import Visit
        self.fields['visit'] = serializers.PrimaryKeyRelatedField(
            queryset=Visit.objects.filter(status='OPEN'),
            help_text="Visit ID for this insurance record"
        )
        self.fields['provider'] = serializers.PrimaryKeyRelatedField(
            queryset=HMOProvider.objects.filter(is_active=True),
            help_text="HMO Provider ID"
        )
    
    def validate_visit(self, value):
        """Ensure visit is OPEN."""
        if value.status == 'CLOSED':
            raise serializers.ValidationError(
                "Cannot add insurance to a CLOSED visit. Closed visits are immutable."
            )
        return value
    
    def validate_coverage_percentage(self, value):
        """Ensure coverage percentage is valid."""
        if value < 0 or value > 100:
            raise serializers.ValidationError(
                "Coverage percentage must be between 0 and 100."
            )
        return value
    
    def validate(self, attrs):
        """Validate insurance data."""
        # Ensure visit is provided
        if 'visit' not in attrs:
            raise serializers.ValidationError("Visit is required to create insurance record.")
        
        # Ensure provider is provided
        if 'provider' not in attrs:
            raise serializers.ValidationError("Provider is required to create insurance record.")
        
        # For FULL coverage, ensure percentage is 100
        coverage_type = attrs.get('coverage_type', 'FULL')
        coverage_percentage = attrs.get('coverage_percentage', 100)
        
        if coverage_type == 'FULL' and coverage_percentage != 100:
            raise serializers.ValidationError(
                "FULL coverage must have coverage_percentage = 100."
            )
        
        return attrs


class VisitInsuranceUpdateSerializer(VisitInsuranceSerializer):
    """
    Serializer for updating Visit Insurance (Receptionist only).
    
    Can update:
    - approval_status
    - approved_amount (when status is APPROVED)
    - approval_reference
    - approval_date
    - rejection_reason (when status is REJECTED)
    - notes
    """
    
    def validate_approval_status(self, value):
        """Validate approval status changes."""
        if self.instance and value == 'APPROVED':
            # approved_amount can be 0; only reject if completely missing (will be defaulted in validate())
            if 'approved_amount' not in self.initial_data and not getattr(self.instance, 'approved_amount', None):
                raise serializers.ValidationError(
                    "Approved amount must be provided when status is APPROVED."
                )
        if self.instance and value == 'REJECTED':
            if not self.initial_data.get('rejection_reason') and not getattr(self.instance, 'rejection_reason', None):
                raise serializers.ValidationError(
                    "Rejection reason must be provided when status is REJECTED."
                )
        return value
    
    def validate(self, attrs):
        """Validate insurance update data. Default approved_amount from billing summary when APPROVED."""
        approval_status = attrs.get('approval_status')
        if approval_status == 'APPROVED':
            approved_amount = attrs.get('approved_amount')
            if approved_amount is None and not self.instance.approved_amount:
                # Default to visit's computed insurance amount so frontend can omit it
                from .billing_service import BillingService
                summary = BillingService.compute_billing_summary(self.instance.visit)
                attrs['approved_amount'] = summary.insurance_amount
        elif approval_status == 'REJECTED':
            if not attrs.get('rejection_reason') and not self.instance.rejection_reason:
                raise serializers.ValidationError(
                    "Rejection reason must be provided when status is REJECTED."
                )
        
        return attrs

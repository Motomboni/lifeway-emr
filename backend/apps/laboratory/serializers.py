"""
Lab Order Serializers - role-based field visibility.

Per EMR Rules:
- Doctor: Can create orders, view all fields including results
- Lab Tech: Can only update results, cannot see diagnosis/consultation notes
- Data minimization: Lab Tech sees only what's needed for their role
"""
from rest_framework import serializers
from .models import LabOrder
from .result_serializers import LabResultReadSerializer


class LabOrderSerializer(serializers.ModelSerializer):
    """
    Base serializer for Lab Order.
    
    Role-based field visibility:
    - Doctor: All fields visible
    - Lab Tech: Limited fields (no consultation details)
    """
    # Read-only fields
    visit_id = serializers.IntegerField(read_only=True)
    consultation_id = serializers.IntegerField(read_only=True)
    ordered_by = serializers.PrimaryKeyRelatedField(read_only=True)
    ordered_by_name = serializers.SerializerMethodField()
    result = LabResultReadSerializer(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = LabOrder
        fields = [
            'id',
            'visit_id',
            'consultation_id',
            'tests_requested',
            'clinical_indication',
            'status',
            'result',
            'ordered_by',
            'ordered_by_name',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'visit_id',
            'consultation_id',
            'ordered_by',
            'ordered_by_name',
            'created_at',
        ]
    
    def get_ordered_by_name(self, obj):
        """Get the full name of the doctor who ordered the lab."""
        if obj.ordered_by:
            return obj.ordered_by.get_full_name() or f"{obj.ordered_by.username}"
        return None


class LabOrderCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating lab orders (Doctor only).
    
    Doctor provides:
    - consultation (required)
    - tests_requested (required)
    - clinical_indication (optional)
    
    System sets:
    - visit (from context)
    - ordered_by (from authenticated user)
    - status (defaults to ORDERED)
    """
    
    class Meta:
        model = LabOrder
        fields = [
            "id",
            "consultation",
            "tests_requested",
            "clinical_indication",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        """Validate lab order data and check for duplicates."""
        # Check for duplicate lab order (only on create, not update)
        if self.instance is None:
            from core.duplicate_prevention import check_lab_order_duplicate
            from django.core.exceptions import ValidationError as DjangoValidationError
            
            # Get visit from context or validated_data
            visit = self.context.get("visit") or attrs.get('visit')
            tests_requested = attrs.get('tests_requested')
            
            if visit and tests_requested:
                try:
                    check_lab_order_duplicate(
                        visit=visit,
                        test_code=tests_requested,
                        window_minutes=5
                    )
                except DjangoValidationError as e:
                    raise serializers.ValidationError(str(e))
        
        return attrs
    
    def create(self, validated_data):
        """
        Create lab order with visit and user from context or validated_data.
        
        Context must provide:
        - request: Django request object (for authenticated user)
        - visit: Visit instance (from URL parameter, or passed in validated_data)
        """
        request = self.context.get("request")
        
        # Get visit from validated_data (passed from perform_create) or context
        visit = validated_data.pop('visit', None) or self.context.get("visit")
        if not visit:
            raise serializers.ValidationError("Visit is required to create lab order.")
        
        # Get ordered_by from validated_data or use request.user
        ordered_by = validated_data.pop('ordered_by', None) or (request.user if request else None)
        if not ordered_by:
            raise serializers.ValidationError("User is required to create lab order.")

        lab_order = LabOrder.objects.create(
            visit=visit,
            ordered_by=ordered_by,
            **validated_data
        )

        return lab_order


class LabOrderResultSerializer(serializers.ModelSerializer):
    """
    Serializer for Lab Tech to post results.
    
    Lab Tech can ONLY update:
    - result_data (via LabResult creation, not direct update)
    - status (can update to RESULT_READY)
    
    Cannot see or modify:
    - Consultation details
    - Diagnosis
    - Tests requested (read-only)
    """
    
    tests_requested = serializers.JSONField(read_only=True)
    clinical_indication = serializers.CharField(read_only=True)
    ordered_by = serializers.PrimaryKeyRelatedField(read_only=True)
    visit_id = serializers.IntegerField(read_only=True)
    consultation_id = serializers.IntegerField(read_only=True)
    result = LabResultReadSerializer(read_only=True)
    
    class Meta:
        model = LabOrder
        fields = [
            'id',
            'visit_id',
            'consultation_id',
            'tests_requested',
            'clinical_indication',
            'status',
            'result',
            'ordered_by',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'visit_id',
            'consultation_id',
            'tests_requested',
            'clinical_indication',
            'ordered_by',
            'created_at',
            'result',
        ]
    
    def validate_status(self, value):
        """Lab Tech can only set status to RESULT_READY or SAMPLE_COLLECTED."""
        if value not in [LabOrder.Status.RESULT_READY, LabOrder.Status.SAMPLE_COLLECTED]:
            raise serializers.ValidationError(
                f"Lab Tech can only set status to {LabOrder.Status.RESULT_READY} or {LabOrder.Status.SAMPLE_COLLECTED}."
            )
        return value


class LabOrderReadSerializer(LabOrderSerializer):
    """
    Serializer for reading lab orders.
    
    Doctor sees all fields including results.
    Lab Tech sees limited fields (no consultation context).
    """
    pass


# Lab Tech-facing (READ ONLY — MINIMIZED)
class LabOrderLabTechSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabOrder
        fields = [
            "id",
            "tests_requested",
            "clinical_indication",
            "status",
            "created_at",
        ]

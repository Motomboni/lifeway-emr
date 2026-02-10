"""
Lab Result Serializers - Lab Tech only.

Per EMR Rules:
- Lab Tech: Can create results (immutable once created)
- Doctor: Can view results (read-only)
- Data minimization: Lab Tech sees only what's needed
"""
from rest_framework import serializers
from .models import LabResult, LabOrder


class LabResultCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating lab results (Lab Tech only).
    
    Lab Tech provides:
    - lab_order (required - ID of the lab order)
    - result_data (required)
    - abnormal_flag (optional, defaults to NORMAL)
    
    System sets:
    - recorded_by (from authenticated user)
    - recorded_at (auto)
    """
    
    lab_order = serializers.PrimaryKeyRelatedField(
        queryset=LabOrder.objects.all(),
        help_text="Lab order this result belongs to"
    )
    
    class Meta:
        model = LabResult
        fields = [
            "id",
            "lab_order",
            "result_data",
            "abnormal_flag",
        ]
        read_only_fields = ["id"]
    
    def validate_lab_order(self, value):
        """Ensure lab order belongs to the visit and is ORDERED."""
        # Visit is from context (visit-scoped endpoint)
        visit = self.context.get('visit')
        if visit and value.visit_id != visit.id:
            raise serializers.ValidationError(
                "Lab order does not belong to this visit."
            )
        
        if value.status != 'ORDERED':
            raise serializers.ValidationError(
                "Lab result can only be recorded for ORDERED lab orders."
            )
        
        # Check if result already exists
        if hasattr(value, 'result'):
            raise serializers.ValidationError(
                "Lab result already exists for this order. Results are immutable."
            )
        
        return value
    
    def validate_result_data(self, value):
        """Ensure result data is provided."""
        if not value or not value.strip():
            raise serializers.ValidationError(
                "Result data is required."
            )
        return value
    
    def create(self, validated_data):
        """
        Create lab result with user from context.
        
        Context must provide:
        - request: Django request object (for authenticated user)
        - visit: Visit instance (from URL parameter)
        """
        request = self.context["request"]
        
        lab_result = LabResult.objects.create(
            recorded_by=request.user,
            **validated_data
        )
        
        return lab_result


class LabResultReadSerializer(serializers.ModelSerializer):
    """
    Serializer for reading lab results.
    
    Doctor: Sees all fields
    Lab Tech: Sees all fields (they created it)
    """
    
    lab_order_id = serializers.IntegerField(source='lab_order.id', read_only=True)
    recorded_by = serializers.PrimaryKeyRelatedField(read_only=True)
    recorded_at = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = LabResult
        fields = [
            "id",
            "lab_order_id",
            "result_data",
            "abnormal_flag",
            "recorded_by",
            "recorded_at",
        ]
        read_only_fields = [
            "id",
            "lab_order_id",
            "result_data",
            "abnormal_flag",
            "recorded_by",
            "recorded_at",
        ]

"""
Radiology Result Serializers - Radiology Tech only.

Per EMR Rules:
- Radiology Tech: Can create results (immutable once created)
- Doctor: Can view results (read-only)
- Data minimization: Radiology Tech sees only what's needed
"""
from rest_framework import serializers
from .models import RadiologyResult, RadiologyOrder


class RadiologyResultCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating radiology results (Radiology Tech only).
    
    Radiology Tech provides:
    - radiology_order (required - ID of the radiology order)
    - report (required)
    - finding_flag (optional, defaults to NORMAL)
    - image_count (optional, defaults to 0)
    - image_metadata (optional, JSON)
    
    System sets:
    - reported_by (from authenticated user)
    - reported_at (auto)
    """
    
    radiology_order = serializers.PrimaryKeyRelatedField(
        queryset=RadiologyOrder.objects.all(),
        help_text="Radiology order this result belongs to"
    )
    
    class Meta:
        model = RadiologyResult
        fields = [
            "id",
            "radiology_order",
            "report",
            "finding_flag",
            "image_count",
            "image_metadata",
        ]
        read_only_fields = ["id"]
    
    def validate_radiology_order(self, value):
        """Ensure radiology order belongs to the visit and is ORDERED or PERFORMED."""
        # Visit is from context (visit-scoped endpoint)
        visit = self.context.get('visit')
        if visit and value.visit_id != visit.id:
            raise serializers.ValidationError(
                "Radiology order does not belong to this visit."
            )
        
        if value.status not in ['ORDERED', 'PERFORMED']:
            raise serializers.ValidationError(
                "Radiology result can only be recorded for ORDERED or PERFORMED radiology orders."
            )
        
        # Check if result already exists
        if hasattr(value, 'result'):
            raise serializers.ValidationError(
                "Radiology result already exists for this order. Results are immutable."
            )
        
        return value
    
    def validate_report(self, value):
        """Ensure report is provided."""
        if not value or not value.strip():
            raise serializers.ValidationError(
                "Report is required."
            )
        return value
    
    def create(self, validated_data):
        """
        Create radiology result with user from context.
        
        Context must provide:
        - request: Django request object (for authenticated user)
        - visit: Visit instance (from URL parameter)
        """
        request = self.context["request"]
        
        radiology_result = RadiologyResult.objects.create(
            reported_by=request.user,
            **validated_data
        )
        
        return radiology_result


class RadiologyResultReadSerializer(serializers.ModelSerializer):
    """
    Serializer for reading radiology results.
    
    Doctor: Sees all fields
    Radiology Tech: Sees all fields (they created it)
    """
    
    radiology_order_id = serializers.IntegerField(source='radiology_order.id', read_only=True)
    reported_by = serializers.PrimaryKeyRelatedField(read_only=True)
    reported_at = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = RadiologyResult
        fields = [
            "id",
            "radiology_order_id",
            "report",
            "finding_flag",
            "image_count",
            "image_metadata",
            "reported_by",
            "reported_at",
        ]
        read_only_fields = [
            "id",
            "radiology_order_id",
            "report",
            "finding_flag",
            "image_count",
            "image_metadata",
            "reported_by",
            "reported_at",
        ]

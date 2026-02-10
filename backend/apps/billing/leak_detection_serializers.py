"""
Serializers for Revenue Leak Detection.
"""
from rest_framework import serializers
from .leak_detection_models import LeakRecord


class LeakRecordSerializer(serializers.ModelSerializer):
    """Serializer for LeakRecord."""
    
    entity_type_display = serializers.CharField(source='get_entity_type_display', read_only=True)
    visit_id = serializers.IntegerField(source='visit.id', read_only=True)
    visit_patient_name = serializers.SerializerMethodField()
    resolved_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = LeakRecord
        fields = [
            'id',
            'entity_type',
            'entity_type_display',
            'entity_id',
            'service_code',
            'service_name',
            'estimated_amount',
            'visit_id',
            'visit_patient_name',
            'detected_at',
            'resolved_at',
            'resolved_by',
            'resolved_by_name',
            'resolution_notes',
            'detection_context',
        ]
        read_only_fields = ['id', 'detected_at']
    
    def get_visit_patient_name(self, obj):
        """Get patient name from visit."""
        if obj.visit and obj.visit.patient:
            return obj.visit.patient.get_full_name()
        return None
    
    def get_resolved_by_name(self, obj):
        """Get resolver name."""
        if obj.resolved_by:
            return obj.resolved_by.get_full_name()
        return None
    
    def get_is_resolved(self, obj):
        """Check if leak is resolved."""
        return obj.is_resolved()


class LeakRecordResolveSerializer(serializers.Serializer):
    """Serializer for resolving a leak."""
    
    resolution_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Notes about how the leak was resolved"
    )


class DailyAggregationSerializer(serializers.Serializer):
    """Serializer for daily leak aggregation."""
    
    date = serializers.DateField()
    total_leaks = serializers.IntegerField()
    total_estimated_loss = serializers.DecimalField(max_digits=10, decimal_places=2)
    unresolved = serializers.DictField()
    resolved = serializers.DictField()
    by_entity_type = serializers.ListField()


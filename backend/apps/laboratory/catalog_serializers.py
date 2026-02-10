"""
Serializers for Lab Test Catalog.
"""
from rest_framework import serializers
from .catalog_models import LabTestCatalog


class LabTestCatalogSerializer(serializers.ModelSerializer):
    """Base serializer for LabTestCatalog."""
    
    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True
    )
    
    reference_range_display = serializers.CharField(
        source='get_reference_range_display',
        read_only=True
    )
    
    class Meta:
        model = LabTestCatalog
        fields = [
            'id',
            'test_code',
            'test_name',
            'category',
            'description',
            'reference_range_min',
            'reference_range_max',
            'reference_range_text',
            'reference_range_display',
            'unit',
            'is_active',
            'requires_fasting',
            'turnaround_time_hours',
            'specimen_type',
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


class LabTestCatalogCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating lab test catalog entries."""
    
    class Meta:
        model = LabTestCatalog
        fields = [
            'test_code',
            'test_name',
            'category',
            'description',
            'reference_range_min',
            'reference_range_max',
            'reference_range_text',
            'unit',
            'is_active',
            'requires_fasting',
            'turnaround_time_hours',
            'specimen_type',
        ]
    
    def validate_test_code(self, value):
        """Ensure test code is unique."""
        if self.instance and self.instance.test_code == value:
            return value
        
        if LabTestCatalog.objects.filter(test_code=value).exists():
            raise serializers.ValidationError(
                f"Test code '{value}' already exists."
            )
        return value
    
    def create(self, validated_data):
        """Create lab test catalog entry with user context."""
        user = self.context['request'].user
        validated_data['created_by'] = user
        return super().create(validated_data)

"""
Serializers for Radiology Study Types Catalog.
"""
from rest_framework import serializers
from .study_types_models import RadiologyStudyType


class RadiologyStudyTypeSerializer(serializers.ModelSerializer):
    """Base serializer for RadiologyStudyType."""
    
    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = RadiologyStudyType
        fields = [
            'id',
            'study_code',
            'study_name',
            'category',
            'description',
            'protocol',
            'preparation_instructions',
            'contrast_required',
            'contrast_type',
            'estimated_duration_minutes',
            'body_part',
            'is_active',
            'requires_sedation',
            'radiation_dose',
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


class RadiologyStudyTypeCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating radiology study type catalog entries."""
    
    class Meta:
        model = RadiologyStudyType
        fields = [
            'study_code',
            'study_name',
            'category',
            'description',
            'protocol',
            'preparation_instructions',
            'contrast_required',
            'contrast_type',
            'estimated_duration_minutes',
            'body_part',
            'is_active',
            'requires_sedation',
            'radiation_dose',
        ]
    
    def validate_study_code(self, value):
        """Ensure study code is unique."""
        if self.instance and self.instance.study_code == value:
            return value
        
        if RadiologyStudyType.objects.filter(study_code=value).exists():
            raise serializers.ValidationError(
                f"Study code '{value}' already exists."
            )
        return value
    
    def validate(self, attrs):
        """Validate study type data."""
        # Ensure contrast type is provided if contrast is required
        if attrs.get('contrast_required') and not attrs.get('contrast_type'):
            raise serializers.ValidationError(
                "Contrast type must be specified when contrast is required."
            )
        return attrs
    
    def create(self, validated_data):
        """Create radiology study type catalog entry with user context."""
        user = self.context['request'].user
        validated_data['created_by'] = user
        return super().create(validated_data)

"""
Serializers for Radiology Test Templates.
"""
from rest_framework import serializers
from .template_models import RadiologyTestTemplate


class RadiologyTestTemplateSerializer(serializers.ModelSerializer):
    """Serializer for Radiology Test Templates."""
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = RadiologyTestTemplate
        fields = [
            'id',
            'name',
            'category',
            'description',
            'imaging_type',
            'body_part',
            'study_code',
            'default_clinical_indication',
            'default_priority',
            'created_by',
            'created_by_name',
            'is_active',
            'usage_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_by_name', 'usage_count', 'created_at', 'updated_at']
    
    def get_created_by_name(self, obj):
        """Get the full name of the user who created the template."""
        try:
            if not obj.created_by:
                return 'Unknown'
            
            # Try first_name + last_name first
            first_name = getattr(obj.created_by, 'first_name', None) or ''
            last_name = getattr(obj.created_by, 'last_name', None) or ''
            if first_name or last_name:
                full_name = f"{first_name} {last_name}".strip()
                if full_name:
                    return full_name
            
            # Fallback to get_full_name method if available
            if hasattr(obj.created_by, 'get_full_name'):
                try:
                    full_name = obj.created_by.get_full_name()
                    if full_name:
                        return full_name
                except Exception:
                    pass
            
            # Final fallback to username
            return getattr(obj.created_by, 'username', 'Unknown')
        except Exception:
            return 'Unknown'


class RadiologyTestTemplateCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Radiology Test Templates."""
    
    class Meta:
        model = RadiologyTestTemplate
        fields = [
            'name',
            'category',
            'description',
            'imaging_type',
            'body_part',
            'study_code',
            'default_clinical_indication',
            'default_priority',
            'is_active',
        ]


"""
Serializers for Lab Test Templates.
"""
from rest_framework import serializers
from .template_models import LabTestTemplate


class LabTestTemplateSerializer(serializers.ModelSerializer):
    """Serializer for Lab Test Templates."""
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = LabTestTemplate
        fields = [
            'id',
            'name',
            'category',
            'description',
            'tests',
            'default_clinical_indication',
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


class LabTestTemplateCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Lab Test Templates."""
    
    class Meta:
        model = LabTestTemplate
        fields = [
            'name',
            'category',
            'description',
            'tests',
            'default_clinical_indication',
            'is_active',
        ]
    
    def validate_tests(self, value):
        """Validate tests is a non-empty list."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Tests must be a list")
        if len(value) == 0:
            raise serializers.ValidationError("Template must include at least one test")
        return value


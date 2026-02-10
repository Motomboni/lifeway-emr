"""
Serializer for Consultation model - strictly visit-scoped.

Per EMR rules:
- Consultation cannot exist without Visit
- All fields are PHI (Protected Health Information)
- Visit must be OPEN and payment CLEARED (enforced in view)
"""
from rest_framework import serializers
from .models import Consultation
from .diagnosis_models import DiagnosisCode


class ConsultationSerializer(serializers.ModelSerializer):
    """
    Serializer for Consultation - visit-scoped clinical documentation.
    
    Validation:
    - Visit is set from URL parameter (visit_id)
    - created_by is set from authenticated user
    - Visit status and payment checks are in ViewSet
    """
    
    # Read-only fields set by the system
    visit_id = serializers.IntegerField(read_only=True)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    
    # Optional field to merge with patient medical history
    merge_with_patient_record = serializers.BooleanField(
        required=False,
        default=False,
        write_only=True,
        help_text="If True, merge this consultation data into patient's medical history"
    )
    
    class Meta:
        model = Consultation
        fields = [
            'id',
            'visit_id',
            'created_by',
            'created_by_name',
            'history',
            'examination',
            'diagnosis',
            'clinical_notes',
            'merge_with_patient_record',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'visit_id', 'created_by', 'created_by_name', 'created_at', 'updated_at']
    
    def validate(self, attrs):
        """
        Additional validation - visit context is handled in ViewSet.
        This ensures no consultation can be created outside visit context.
        """
        # Visit is set from URL, not from request data
        if 'visit' in attrs:
            raise serializers.ValidationError(
                "Visit cannot be set directly. It is derived from URL parameter."
            )
        
        return attrs


class DiagnosisCodeSerializer(serializers.ModelSerializer):
    """Serializer for diagnosis codes."""
    
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = DiagnosisCode
        fields = [
            'id',
            'code_type',
            'code',
            'description',
            'is_primary',
            'confidence',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_by_name', 'created_at', 'updated_at']
    
    def validate(self, attrs):
        """Validate diagnosis code data."""
        # Ensure code is uppercase
        if 'code' in attrs:
            attrs['code'] = attrs['code'].strip().upper()
        
        # Ensure description is not empty
        if 'description' in attrs:
            attrs['description'] = attrs['description'].strip()
            if not attrs['description']:
                raise serializers.ValidationError({
                    'description': 'Description cannot be empty'
                })
        
        return attrs


class ConsultationWithCodesSerializer(ConsultationSerializer):
    """Extended consultation serializer that includes diagnosis codes."""
    
    diagnosis_codes = DiagnosisCodeSerializer(many=True, read_only=True)
    
    class Meta(ConsultationSerializer.Meta):
        fields = ConsultationSerializer.Meta.fields + ['diagnosis_codes']

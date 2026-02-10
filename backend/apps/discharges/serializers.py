"""
Serializers for DischargeSummary model.
"""
from rest_framework import serializers
from .models import DischargeSummary


class DischargeSummarySerializer(serializers.ModelSerializer):
    """Base serializer for DischargeSummary."""
    
    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True
    )
    
    visit_id = serializers.IntegerField(source='visit.id', read_only=True)
    consultation_id = serializers.IntegerField(source='consultation.id', read_only=True)
    patient_name = serializers.CharField(
        source='visit.patient.get_full_name',
        read_only=True
    )
    patient_id = serializers.IntegerField(
        source='visit.patient.id',
        read_only=True
    )
    
    class Meta:
        model = DischargeSummary
        fields = [
            'id',
            'visit_id',
            'consultation_id',
            'patient_id',
            'patient_name',
            'chief_complaint',
            'admission_date',
            'discharge_date',
            'diagnosis',
            'procedures_performed',
            'treatment_summary',
            'medications_on_discharge',
            'follow_up_instructions',
            'condition_at_discharge',
            'discharge_disposition',
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


class DischargeSummaryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating discharge summaries (Doctor only)."""
    
    class Meta:
        model = DischargeSummary
        fields = [
            'consultation',
            'chief_complaint',
            'admission_date',
            'discharge_date',
            'diagnosis',
            'procedures_performed',
            'treatment_summary',
            'medications_on_discharge',
            'follow_up_instructions',
            'condition_at_discharge',
            'discharge_disposition',
        ]
    
    def validate_consultation(self, value):
        """Ensure consultation belongs to the visit."""
        visit_id = self.context.get('visit_id')
        if visit_id and value.visit_id != visit_id:
            raise serializers.ValidationError(
                "Consultation must belong to the same visit."
            )
        return value
    
    def validate(self, attrs):
        """Validate discharge summary data."""
        visit_id = self.context.get('visit_id')
        if visit_id:
            from apps.visits.models import Visit
            try:
                visit = Visit.objects.get(pk=visit_id)
                if visit.status != 'CLOSED':
                    raise serializers.ValidationError(
                        "Discharge summary can only be created for CLOSED visits."
                    )
            except Visit.DoesNotExist:
                raise serializers.ValidationError("Visit not found.")
        
        # Ensure discharge date is after admission date
        if attrs.get('discharge_date') and attrs.get('admission_date'):
            if attrs['discharge_date'] < attrs['admission_date']:
                raise serializers.ValidationError(
                    "Discharge date must be after admission date."
                )
        
        return attrs
    
    def create(self, validated_data):
        """Create discharge summary with visit and doctor context."""
        visit_id = self.context.get('visit_id')
        user = self.context['request'].user
        
        validated_data['visit_id'] = visit_id
        validated_data['created_by'] = user
        
        return super().create(validated_data)

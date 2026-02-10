"""
Serializers for AI Integration API.

Per EMR Rules:
- Visit-scoped requests
- Role-based field visibility
- Audit logging
"""
from rest_framework import serializers
from .models import AIRequest, AIConfiguration, AIFeatureType, AIProvider, ClinicalNote
from apps.visits.models import Visit
from apps.consultations.models import Consultation


class AIRequestSerializer(serializers.ModelSerializer):
    """Serializer for AI request tracking (read-only for compliance)."""
    feature_type_display = serializers.CharField(source='get_feature_type_display', read_only=True)
    provider_display = serializers.CharField(source='get_provider_display', read_only=True)
    visit_id = serializers.IntegerField(source='visit.id', read_only=True)
    
    class Meta:
        model = AIRequest
        fields = [
            'id',
            'visit_id',
            'user',
            'user_role',
            'feature_type',
            'feature_type_display',
            'provider',
            'provider_display',
            'model_name',
            'prompt_tokens',
            'completion_tokens',
            'total_tokens',
            'cost_usd',
            'success',
            'error_message',
            'response_time_ms',
            'timestamp',
        ]
        read_only_fields = '__all__'


class ClinicalDecisionSupportRequestSerializer(serializers.Serializer):
    """Serializer for clinical decision support requests."""
    consultation_id = serializers.IntegerField(required=False)
    patient_symptoms = serializers.CharField(required=False, allow_blank=True)
    patient_history = serializers.CharField(required=False, allow_blank=True)
    current_medications = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )
    include_differential_diagnosis = serializers.BooleanField(default=True)
    include_treatment_suggestions = serializers.BooleanField(default=True)
    
    def validate(self, attrs):
        """Validate that at least one input is provided."""
        if not any([
            attrs.get('consultation_id'),
            attrs.get('patient_symptoms'),
            attrs.get('patient_history'),
        ]):
            raise serializers.ValidationError(
                "At least one of consultation_id, patient_symptoms, or patient_history must be provided."
            )
        return attrs


class ClinicalDecisionSupportResponseSerializer(serializers.Serializer):
    """Serializer for clinical decision support responses."""
    suggested_diagnoses = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of suggested diagnoses with confidence scores"
    )
    differential_diagnosis = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="Differential diagnosis options"
    )
    treatment_suggestions = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="Treatment suggestions"
    )
    warnings = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Clinical warnings or alerts"
    )
    request_id = serializers.IntegerField(help_text="AI request ID for audit trail")


class NLPSummarizationRequestSerializer(serializers.Serializer):
    """Serializer for NLP summarization requests."""
    consultation_id = serializers.IntegerField(required=False)
    text = serializers.CharField(required=False, allow_blank=True)
    summary_type = serializers.ChoiceField(
        choices=['brief', 'detailed', 'structured'],
        default='brief'
    )
    
    def validate(self, attrs):
        """Validate that at least one input is provided."""
        if not attrs.get('consultation_id') and not attrs.get('text'):
            raise serializers.ValidationError(
                "Either consultation_id or text must be provided."
            )
        return attrs


class NLPSummarizationResponseSerializer(serializers.Serializer):
    """Serializer for NLP summarization responses."""
    summary = serializers.CharField(help_text="Generated summary")
    key_points = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Key points extracted"
    )
    request_id = serializers.IntegerField(help_text="AI request ID for audit trail")


class AutomatedCodingRequestSerializer(serializers.Serializer):
    """Serializer for automated coding requests."""
    consultation_id = serializers.IntegerField(required=True)
    code_types = serializers.ListField(
        child=serializers.ChoiceField(choices=['icd11', 'cpt']),
        default=['icd11'],
        help_text="Types of codes to generate"
    )


class AutomatedCodingResponseSerializer(serializers.Serializer):
    """Serializer for automated coding responses."""
    icd11_codes = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="Suggested ICD-11 codes"
    )
    cpt_codes = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="Suggested CPT codes"
    )
    request_id = serializers.IntegerField(help_text="AI request ID for audit trail")


class DrugInteractionCheckRequestSerializer(serializers.Serializer):
    """Serializer for drug interaction check requests."""
    current_medications = serializers.ListField(
        child=serializers.CharField(),
        required=True,
        min_length=1,
        help_text="List of current medications"
    )
    new_medication = serializers.CharField(required=True, help_text="New medication to check")


class DrugInteractionCheckResponseSerializer(serializers.Serializer):
    """Serializer for drug interaction check responses."""
    has_interaction = serializers.BooleanField(help_text="Whether interaction exists")
    severity = serializers.ChoiceField(
        choices=['mild', 'moderate', 'severe', 'contraindicated'],
        required=False,
        help_text="Severity of interaction"
    )
    description = serializers.CharField(required=False, help_text="Description of interaction")
    recommendations = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Recommendations"
    )
    request_id = serializers.IntegerField(help_text="AI request ID for audit trail")


class AIConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for AI configuration (admin only)."""
    
    class Meta:
        model = AIConfiguration
        fields = [
            'id',
            'feature_type',
            'default_provider',
            'default_model',
            'enabled',
            'max_tokens',
            'temperature',
            'rate_limit_per_minute',
            'cost_per_1k_tokens',
            'configuration',
            'updated_at',
            'created_at',
        ]
        read_only_fields = ['updated_at', 'created_at']


class GenerateNoteRequestSerializer(serializers.Serializer):
    """Request for POST /ai/generate-note."""
    transcript = serializers.CharField(required=True, allow_blank=True)
    note_type = serializers.ChoiceField(
        choices=[('SOAP', 'SOAP'), ('summary', 'Summary'), ('discharge', 'Discharge')],
        default='summary',
    )
    appointment_id = serializers.IntegerField(required=False, allow_null=True)


class GenerateNoteResponseSerializer(serializers.Serializer):
    """Response from generate-note (structured note for doctor to edit/approve)."""
    note_type = serializers.CharField()
    structured_note = serializers.CharField()
    raw_transcript = serializers.CharField()
    request_id = serializers.IntegerField(allow_null=True)


class ClinicalNoteSerializer(serializers.ModelSerializer):
    """Serializer for ClinicalNote (save after doctor edit)."""
    class Meta:
        model = ClinicalNote
        fields = [
            'id',
            'patient',
            'doctor',
            'appointment',
            'note_type',
            'raw_transcript',
            'ai_generated_note',
            'doctor_edited_note',
            'created_at',
            'updated_at',
            'approved_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

"""
Serializers for clinical models.
"""
from rest_framework import serializers
from .models import VitalSigns, ClinicalTemplate, ClinicalAlert
from .operation_models import OperationNote
from apps.visits.models import Visit


class VitalSignsSerializer(serializers.ModelSerializer):
    """Serializer for Vital Signs."""
    recorded_by_name = serializers.SerializerMethodField()
    abnormal_flags = serializers.SerializerMethodField()
    
    class Meta:
        model = VitalSigns
        fields = [
            'id',
            'visit',
            'recorded_by',
            'recorded_by_name',
            'temperature',
            'systolic_bp',
            'diastolic_bp',
            'pulse',
            'respiratory_rate',
            'oxygen_saturation',
            'weight',
            'height',
            'bmi',
            'muac',
            'nutritional_status',
            'urine_anc',
            'lmp',
            'edd',
            'ega_weeks',
            'ega_days',
            'notes',
            'recorded_at',
            'abnormal_flags',
        ]
        read_only_fields = ['id', 'recorded_by', 'recorded_at', 'bmi', 'abnormal_flags']
    
    def get_recorded_by_name(self, obj):
        """Get the name of the user who recorded the vital signs."""
        if obj.recorded_by:
            # Try get_full_name first, fallback to username
            try:
                return obj.recorded_by.get_full_name() or obj.recorded_by.username
            except (AttributeError, Exception):
                return obj.recorded_by.username if hasattr(obj.recorded_by, 'username') else 'Unknown'
        return 'Unknown'
    
    def get_abnormal_flags(self, obj):
        """Get list of abnormal vital signs flags."""
        try:
            return obj.get_abnormal_flags()
        except (AttributeError, Exception):
            return []


class VitalSignsCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Vital Signs."""
    
    class Meta:
        model = VitalSigns
        fields = [
            'temperature',
            'systolic_bp',
            'diastolic_bp',
            'pulse',
            'respiratory_rate',
            'oxygen_saturation',
            'weight',
            'height',
            'muac',
            'nutritional_status',
            'urine_anc',
            'lmp',
            'edd',
            'ega_weeks',
            'ega_days',
            'notes',
        ]
    
    def validate_temperature(self, value):
        """Ensure temperature is valid if provided."""
        # Handle empty strings, 0, or None - convert to None for optional field
        if value is None or value == '' or value == 0:
            return None
        
        from decimal import Decimal
        try:
            # Convert to Decimal for consistent comparison
            temp = Decimal(str(value))
            # Ensure it's within valid range (should be handled by model validators, but double-check)
            if temp < 30.0 or temp > 45.0:
                raise serializers.ValidationError("Temperature must be between 30.0 and 45.0 degrees Celsius.")
            return temp
        except (ValueError, TypeError):
            # If conversion fails, return None (optional field)
            return None
    
    def validate_urine_anc(self, value):
        """Handle urine_anc field - convert None to empty string for CharField."""
        # CharField with blank=True accepts empty string, not None
        if value is None:
            return ''
        return value
    
    def validate_nutritional_status(self, value):
        """Handle nutritional_status field - convert None to empty string for CharField."""
        # CharField with blank=True accepts empty string, not None
        if value is None:
            return ''
        return value
    
    def validate(self, attrs):
        """Validate vital signs data and check for duplicates."""
        # Clean up empty strings, 0, or None - convert to None for optional fields
        optional_decimal_fields = ['temperature', 'oxygen_saturation', 'weight', 'height']
        for field in optional_decimal_fields:
            if field in attrs:
                value = attrs[field]
                # Convert empty strings, None, 0, or '0' to None
                if value is None or value == '' or value == 0 or value == '0':
                    attrs[field] = None
                elif isinstance(value, str) and value.strip() == '':
                    attrs[field] = None
                elif isinstance(value, (int, float)) and value == 0:
                    # For temperature, 0 is invalid, so convert to None
                    if field == 'temperature':
                        attrs[field] = None
        
        # Clean up empty strings for integer fields
        optional_int_fields = ['systolic_bp', 'diastolic_bp', 'pulse', 'respiratory_rate']
        for field in optional_int_fields:
            if field in attrs:
                if attrs[field] == '' or attrs[field] is None:
                    attrs[field] = None
        
        # Handle CharField fields that allow blank - convert None to empty string
        # Both urine_anc and nutritional_status are CharFields with blank=True
        if 'urine_anc' in attrs and attrs['urine_anc'] is None:
            attrs['urine_anc'] = ''
        if 'nutritional_status' in attrs and attrs['nutritional_status'] is None:
            attrs['nutritional_status'] = ''
        
        # Check for duplicate vital signs (only on create, not update)
        if self.instance is None:
            from core.duplicate_prevention import check_vital_signs_duplicate
            from django.core.exceptions import ValidationError as DjangoValidationError
            
            visit = self.context.get('visit')
            
            if visit:
                try:
                    check_vital_signs_duplicate(
                        visit=visit,
                        window_minutes=3
                    )
                except DjangoValidationError as e:
                    raise serializers.ValidationError(str(e))
        
        return attrs


class ClinicalTemplateSerializer(serializers.ModelSerializer):
    """Serializer for Clinical Templates."""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = ClinicalTemplate
        fields = [
            'id',
            'name',
            'category',
            'description',
            'history_template',
            'examination_template',
            'diagnosis_template',
            'clinical_notes_template',
            'created_by',
            'created_by_name',
            'is_active',
            'usage_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'usage_count', 'created_at', 'updated_at']


class ClinicalTemplateCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Clinical Templates."""
    
    class Meta:
        model = ClinicalTemplate
        fields = [
            'name',
            'category',
            'description',
            'history_template',
            'examination_template',
            'diagnosis_template',
            'clinical_notes_template',
            'is_active',
        ]


class ClinicalAlertSerializer(serializers.ModelSerializer):
    """Serializer for Clinical Alerts."""
    acknowledged_by_name = serializers.SerializerMethodField()
    
    def get_acknowledged_by_name(self, obj):
        """Safely get acknowledged_by name."""
        if obj.acknowledged_by:
            try:
                # Try get_full_name() first
                full_name = obj.acknowledged_by.get_full_name()
                if full_name:
                    return full_name
            except (AttributeError, Exception):
                pass
            
            # Fallback to first_name + last_name
            try:
                first = getattr(obj.acknowledged_by, 'first_name', '') or ''
                last = getattr(obj.acknowledged_by, 'last_name', '') or ''
                name = f"{first} {last}".strip()
                if name:
                    return name
            except Exception:
                pass
            
            # Final fallback to username or string representation
            try:
                return getattr(obj.acknowledged_by, 'username', None) or str(obj.acknowledged_by)
            except Exception:
                return str(obj.acknowledged_by.id) if hasattr(obj.acknowledged_by, 'id') else 'Unknown'
        return None
    
    class Meta:
        model = ClinicalAlert
        fields = [
            'id',
            'visit',
            'alert_type',
            'severity',
            'title',
            'message',
            'related_resource_type',
            'related_resource_id',
            'acknowledged_by',
            'acknowledged_by_name',
            'acknowledged_at',
            'is_resolved',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'acknowledged_by',
            'acknowledged_at',
            'created_at',
        ]


class OperationNoteSerializer(serializers.ModelSerializer):
    """Serializer for Operation Notes."""
    surgeon_name = serializers.SerializerMethodField()
    assistant_surgeon_name = serializers.SerializerMethodField()
    anesthetist_name = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    
    class Meta:
        model = OperationNote
        fields = [
            'id',
            'visit',
            'consultation',
            'surgeon',
            'surgeon_name',
            'assistant_surgeon',
            'assistant_surgeon_name',
            'anesthetist',
            'anesthetist_name',
            'operation_type',
            'operation_name',
            'preoperative_diagnosis',
            'postoperative_diagnosis',
            'indication',
            'anesthesia_type',
            'anesthesia_notes',
            'procedure_description',
            'findings',
            'technique',
            'complications',
            'estimated_blood_loss',
            'specimens_sent',
            'postoperative_plan',
            'postoperative_instructions',
            'operation_date',
            'operation_duration_minutes',
            'patient_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'surgeon', 'created_at', 'updated_at']
    
    def get_surgeon_name(self, obj):
        """Get surgeon's full name."""
        if obj.surgeon:
            try:
                return obj.surgeon.get_full_name() or obj.surgeon.username
            except (AttributeError, Exception):
                return obj.surgeon.username if hasattr(obj.surgeon, 'username') else 'Unknown'
        return None
    
    def get_assistant_surgeon_name(self, obj):
        """Get assistant surgeon's full name."""
        if obj.assistant_surgeon:
            try:
                return obj.assistant_surgeon.get_full_name() or obj.assistant_surgeon.username
            except (AttributeError, Exception):
                return obj.assistant_surgeon.username if hasattr(obj.assistant_surgeon, 'username') else 'Unknown'
        return None
    
    def get_anesthetist_name(self, obj):
        """Get anesthetist's full name."""
        if obj.anesthetist:
            try:
                return obj.anesthetist.get_full_name() or obj.anesthetist.username
            except (AttributeError, Exception):
                return obj.anesthetist.username if hasattr(obj.anesthetist, 'username') else 'Unknown'
        return None
    
    def get_patient_name(self, obj):
        """Get patient's name."""
        if obj.visit and obj.visit.patient:
            patient = obj.visit.patient
            return f"{patient.first_name} {patient.last_name}".strip()
        return None


class OperationNoteCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Operation Notes."""
    
    class Meta:
        model = OperationNote
        fields = [
            'consultation',
            'assistant_surgeon',
            'anesthetist',
            'operation_type',
            'operation_name',
            'preoperative_diagnosis',
            'postoperative_diagnosis',
            'indication',
            'anesthesia_type',
            'anesthesia_notes',
            'procedure_description',
            'findings',
            'technique',
            'complications',
            'estimated_blood_loss',
            'specimens_sent',
            'postoperative_plan',
            'postoperative_instructions',
            'operation_date',
            'operation_duration_minutes',
        ]

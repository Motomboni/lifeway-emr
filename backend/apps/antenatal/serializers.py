"""
Antenatal Module Serializers

Comprehensive serializers for antenatal clinic management.
"""
from rest_framework import serializers
from .models import (
    AntenatalRecord, AntenatalVisit, AntenatalUltrasound,
    AntenatalLab, AntenatalMedication, AntenatalOutcome
)


class AntenatalRecordListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for antenatal record listing."""
    
    patient_name = serializers.SerializerMethodField()
    current_gestational_age_weeks = serializers.ReadOnlyField()
    current_gestational_age_days = serializers.ReadOnlyField()
    
    class Meta:
        model = AntenatalRecord
        fields = [
            'id', 'patient', 'patient_name', 'pregnancy_number', 'booking_date',
            'lmp', 'edd', 'outcome', 'high_risk', 'current_gestational_age_weeks',
            'current_gestational_age_days', 'created_at'
        ]
    
    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"


class AntenatalRecordDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single antenatal record view."""
    
    patient_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    current_gestational_age_weeks = serializers.ReadOnlyField()
    current_gestational_age_days = serializers.ReadOnlyField()
    
    class Meta:
        model = AntenatalRecord
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'created_by']
    
    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"
    
    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() or obj.created_by.username


class AntenatalRecordCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new antenatal records."""
    
    class Meta:
        model = AntenatalRecord
        fields = [
            'patient', 'pregnancy_number', 'booking_date', 'lmp', 'edd',
            'parity', 'gravida', 'para', 'abortions', 'living_children',
            'past_medical_history', 'past_surgical_history', 'family_history',
            'allergies', 'previous_cs', 'previous_cs_count', 'previous_complications',
            'pregnancy_type', 'high_risk', 'risk_factors', 'clinical_notes'
        ]
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class AntenatalRecordUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating antenatal records."""
    
    class Meta:
        model = AntenatalRecord
        fields = [
            'outcome', 'delivery_date', 'delivery_gestational_age_weeks',
            'delivery_gestational_age_days', 'high_risk', 'risk_factors',
            'clinical_notes'
        ]


class AntenatalVisitSerializer(serializers.ModelSerializer):
    """Serializer for antenatal visits."""
    
    recorded_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AntenatalVisit
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'recorded_by']
    
    def get_recorded_by_name(self, obj):
        return obj.recorded_by.get_full_name() or obj.recorded_by.username


class AntenatalVisitCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating antenatal visits."""
    
    class Meta:
        model = AntenatalVisit
        fields = [
            'antenatal_record', 'visit', 'visit_date', 'visit_type',
            'gestational_age_weeks', 'gestational_age_days', 'chief_complaint',
            'blood_pressure_systolic', 'blood_pressure_diastolic', 'weight',
            'fundal_height', 'fetal_heart_rate', 'fetal_presentation',
            'urine_protein', 'urine_glucose', 'clinical_notes', 'next_appointment_date'
        ]
    
    def create(self, validated_data):
        validated_data['recorded_by'] = self.context['request'].user
        return super().create(validated_data)


class AntenatalUltrasoundSerializer(serializers.ModelSerializer):
    """Serializer for antenatal ultrasounds."""
    
    performed_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AntenatalUltrasound
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'performed_by']
    
    def get_performed_by_name(self, obj):
        return obj.performed_by.get_full_name() or obj.performed_by.username


class AntenatalUltrasoundCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating antenatal ultrasounds."""
    
    class Meta:
        model = AntenatalUltrasound
        fields = [
            'antenatal_visit', 'scan_date', 'scan_type', 'gestational_age_weeks',
            'gestational_age_days', 'crl', 'bpd', 'hc', 'ac', 'fl',
            'estimated_fetal_weight', 'number_of_fetuses', 'fetal_presentation',
            'placenta_location', 'placenta_grade', 'amniotic_fluid', 'findings', 'report'
        ]
    
    def create(self, validated_data):
        validated_data['performed_by'] = self.context['request'].user
        return super().create(validated_data)


class AntenatalLabSerializer(serializers.ModelSerializer):
    """Serializer for antenatal lab tests."""
    
    ordered_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AntenatalLab
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'ordered_by']
    
    def get_ordered_by_name(self, obj):
        return obj.ordered_by.get_full_name() or obj.ordered_by.username


class AntenatalLabCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating antenatal lab tests."""
    
    class Meta:
        model = AntenatalLab
        fields = [
            'antenatal_visit', 'test_name', 'test_date', 'hb', 'pcv',
            'blood_group', 'rhesus', 'hiv', 'hbsag', 'vdrl', 'results', 'notes'
        ]
    
    def create(self, validated_data):
        validated_data['ordered_by'] = self.context['request'].user
        return super().create(validated_data)


class AntenatalMedicationSerializer(serializers.ModelSerializer):
    """Serializer for antenatal medications."""
    
    prescribed_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AntenatalMedication
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'prescribed_by']
    
    def get_prescribed_by_name(self, obj):
        return obj.prescribed_by.get_full_name() or obj.prescribed_by.username


class AntenatalMedicationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating antenatal medications."""
    
    class Meta:
        model = AntenatalMedication
        fields = [
            'antenatal_visit', 'medication_name', 'category', 'dose', 'frequency',
            'duration', 'start_date', 'end_date', 'notes'
        ]
    
    def create(self, validated_data):
        validated_data['prescribed_by'] = self.context['request'].user
        return super().create(validated_data)


class AntenatalOutcomeSerializer(serializers.ModelSerializer):
    """Serializer for antenatal outcomes."""
    
    recorded_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AntenatalOutcome
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'recorded_by']
    
    def get_recorded_by_name(self, obj):
        return obj.recorded_by.get_full_name() or obj.recorded_by.username


class AntenatalOutcomeCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating antenatal outcomes."""
    
    class Meta:
        model = AntenatalOutcome
        fields = [
            'antenatal_record', 'delivery_date', 'delivery_time', 'delivery_type',
            'delivery_gestational_age_weeks', 'delivery_gestational_age_days',
            'number_of_babies', 'live_births', 'stillbirths', 'baby_1_gender',
            'baby_1_weight', 'baby_1_apgar_1min', 'baby_1_apgar_5min',
            'additional_babies', 'maternal_complications', 'neonatal_complications', 'notes'
        ]
    
    def create(self, validated_data):
        validated_data['recorded_by'] = self.context['request'].user
        return super().create(validated_data)

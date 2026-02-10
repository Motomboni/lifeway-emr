"""
IVF Module Serializers

Comprehensive serializers for IVF treatment data.
"""
from rest_framework import serializers
from .models import (
    IVFCycle, OvarianStimulation, OocyteRetrieval, SpermAnalysis,
    Embryo, EmbryoTransfer, IVFMedication, IVFOutcome, IVFConsent
)


class IVFPatientListSerializer(serializers.Serializer):
    """Minimal patient fields for IVF patients list (patients with at least one IVF cycle)."""
    id = serializers.IntegerField(read_only=True)
    patient_id = serializers.CharField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    cycle_count = serializers.IntegerField(read_only=True)


class IVFCycleListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for cycle listing."""
    
    patient_name = serializers.SerializerMethodField()
    partner_name = serializers.SerializerMethodField()
    
    class Meta:
        model = IVFCycle
        fields = [
            'id', 'patient', 'patient_name', 'partner', 'partner_name',
            'cycle_number', 'cycle_type', 'status', 'planned_start_date',
            'actual_start_date', 'consent_signed', 'pregnancy_outcome',
            'created_at'
        ]
    
    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"
    
    def get_partner_name(self, obj):
        if obj.partner:
            return f"{obj.partner.first_name} {obj.partner.last_name}"
        return None


class IVFCycleDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single cycle view."""
    
    patient_name = serializers.SerializerMethodField()
    partner_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = IVFCycle
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'created_by']
    
    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"
    
    def get_partner_name(self, obj):
        if obj.partner:
            return f"{obj.partner.first_name} {obj.partner.last_name}"
        return None
    
    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() or obj.created_by.username


class IVFCycleCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new IVF cycles."""
    
    class Meta:
        model = IVFCycle
        fields = [
            'patient', 'partner', 'cycle_type', 'planned_start_date',
            'lmp_date', 'protocol', 'diagnosis', 'estimated_cost',
            'insurance_pre_auth', 'insurance_pre_auth_number', 'clinical_notes'
        ]
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class IVFCycleUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating IVF cycles."""
    
    class Meta:
        model = IVFCycle
        fields = [
            'status', 'actual_start_date', 'protocol', 'diagnosis',
            'consent_signed', 'consent_date', 'partner_consent_signed',
            'partner_consent_date', 'pregnancy_test_date', 'beta_hcg_result',
            'pregnancy_outcome', 'estimated_cost', 'clinical_notes'
        ]


class OvarianStimulationSerializer(serializers.ModelSerializer):
    """Serializer for ovarian stimulation records."""
    
    total_follicle_count = serializers.ReadOnlyField()
    leading_follicles = serializers.ReadOnlyField()
    recorded_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = OvarianStimulation
        fields = '__all__'
        read_only_fields = ['created_at', 'recorded_by']
    
    def get_recorded_by_name(self, obj):
        return obj.recorded_by.get_full_name() or obj.recorded_by.username
    
    def create(self, validated_data):
        validated_data['recorded_by'] = self.context['request'].user
        return super().create(validated_data)


class OocyteRetrievalSerializer(serializers.ModelSerializer):
    """Serializer for oocyte retrieval records."""
    
    performed_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = OocyteRetrieval
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'performed_by', 'total_oocytes_retrieved']
    
    def get_performed_by_name(self, obj):
        return obj.performed_by.get_full_name() or obj.performed_by.username
    
    def create(self, validated_data):
        validated_data['performed_by'] = self.context['request'].user
        return super().create(validated_data)


class SpermAnalysisListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for sperm analysis listing."""
    
    patient_name = serializers.SerializerMethodField()
    
    class Meta:
        model = SpermAnalysis
        fields = [
            'id', 'patient', 'patient_name', 'collection_date',
            'concentration', 'total_motility', 'normal_forms',
            'assessment', 'created_at'
        ]
    
    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"


class SpermAnalysisDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for sperm analysis."""
    
    patient_name = serializers.SerializerMethodField()
    analyzed_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = SpermAnalysis
        fields = '__all__'
        read_only_fields = ['created_at', 'analyzed_by']
    
    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"
    
    def get_analyzed_by_name(self, obj):
        return obj.analyzed_by.get_full_name() or obj.analyzed_by.username
    
    def create(self, validated_data):
        validated_data['analyzed_by'] = self.context['request'].user
        return super().create(validated_data)


class EmbryoListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for embryo listing."""
    
    class Meta:
        model = Embryo
        fields = [
            'id', 'lab_id', 'embryo_number', 'status',
            'fertilization_method', 'day3_grade', 'blastocyst_grade',
            'pgt_performed', 'pgt_result', 'disposition'
        ]


class EmbryoDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for embryo records."""
    
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Embryo
        fields = '__all__'
        read_only_fields = ['lab_id', 'created_at', 'updated_at', 'created_by']
    
    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() or obj.created_by.username
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class EmbryoTransferSerializer(serializers.ModelSerializer):
    """Serializer for embryo transfer records."""
    
    performed_by_name = serializers.SerializerMethodField()
    embryo_details = EmbryoListSerializer(source='embryos', many=True, read_only=True)
    
    class Meta:
        model = EmbryoTransfer
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'performed_by']
    
    def get_performed_by_name(self, obj):
        return obj.performed_by.get_full_name() or obj.performed_by.username
    
    def create(self, validated_data):
        embryos = validated_data.pop('embryos', [])
        validated_data['performed_by'] = self.context['request'].user
        transfer = super().create(validated_data)
        transfer.embryos.set(embryos)
        return transfer


class IVFMedicationSerializer(serializers.ModelSerializer):
    """Serializer for IVF medications."""
    
    prescribed_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = IVFMedication
        fields = '__all__'
        read_only_fields = ['created_at', 'prescribed_by']
    
    def get_prescribed_by_name(self, obj):
        return obj.prescribed_by.get_full_name() or obj.prescribed_by.username
    
    def create(self, validated_data):
        validated_data['prescribed_by'] = self.context['request'].user
        return super().create(validated_data)


class IVFOutcomeSerializer(serializers.ModelSerializer):
    """Serializer for IVF outcomes."""
    
    recorded_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = IVFOutcome
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'recorded_by']
    
    def get_recorded_by_name(self, obj):
        return obj.recorded_by.get_full_name() or obj.recorded_by.username
    
    def create(self, validated_data):
        validated_data['recorded_by'] = self.context['request'].user
        return super().create(validated_data)


class IVFConsentSerializer(serializers.ModelSerializer):
    """Serializer for IVF consents."""
    
    patient_name = serializers.SerializerMethodField()
    recorded_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = IVFConsent
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'recorded_by']
    
    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"
    
    def get_recorded_by_name(self, obj):
        return obj.recorded_by.get_full_name() or obj.recorded_by.username
    
    def create(self, validated_data):
        validated_data['recorded_by'] = self.context['request'].user
        return super().create(validated_data)


# Nested Cycle Serializer with all related data
class IVFCycleFullSerializer(serializers.ModelSerializer):
    """
    Complete cycle serializer with all related data.
    Used for detailed cycle view.
    """
    
    patient_name = serializers.SerializerMethodField()
    partner_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    
    # Related data
    stimulation_records = OvarianStimulationSerializer(many=True, read_only=True)
    oocyte_retrieval = OocyteRetrievalSerializer(read_only=True)
    sperm_analyses = SpermAnalysisListSerializer(many=True, read_only=True)
    embryos = EmbryoListSerializer(many=True, read_only=True)
    embryo_transfers = EmbryoTransferSerializer(many=True, read_only=True)
    medications = IVFMedicationSerializer(many=True, read_only=True)
    outcome = IVFOutcomeSerializer(read_only=True)
    consents = IVFConsentSerializer(many=True, read_only=True)
    
    # Computed fields
    total_embryos = serializers.SerializerMethodField()
    frozen_embryos = serializers.SerializerMethodField()
    transferred_embryos = serializers.SerializerMethodField()
    
    class Meta:
        model = IVFCycle
        fields = '__all__'
    
    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"
    
    def get_partner_name(self, obj):
        if obj.partner:
            return f"{obj.partner.first_name} {obj.partner.last_name}"
        return None
    
    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() or obj.created_by.username
    
    def get_total_embryos(self, obj):
        return obj.embryos.count()
    
    def get_frozen_embryos(self, obj):
        return obj.embryos.filter(status='FROZEN').count()
    
    def get_transferred_embryos(self, obj):
        return obj.embryos.filter(status='TRANSFERRED').count()


class EmbryoInventorySerializer(serializers.ModelSerializer):
    """
    Serializer for embryo inventory view.
    Provides a flat view of embryos with patient and cycle information.
    """
    
    cycle_id = serializers.IntegerField(source='cycle.id', read_only=True)
    patient_name = serializers.SerializerMethodField()
    partner_name = serializers.SerializerMethodField()
    cycle_number = serializers.IntegerField(source='cycle.cycle_number', read_only=True)
    grade = serializers.SerializerMethodField()
    stage = serializers.SerializerMethodField()
    storage_days = serializers.SerializerMethodField()
    tank_location = serializers.CharField(source='storage_location', read_only=True)
    freeze_date = serializers.DateField(source='frozen_date', read_only=True)
    
    class Meta:
        model = Embryo
        fields = [
            'id', 'cycle_id', 'embryo_number', 'lab_id', 'patient_name',
            'partner_name', 'cycle_number', 'status', 'stage', 'grade',
            'freeze_date', 'storage_days', 'tank_location', 'straw_id',
            'pgt_result'
        ]
    
    def get_patient_name(self, obj):
        return f"{obj.cycle.patient.first_name} {obj.cycle.patient.last_name}"
    
    def get_partner_name(self, obj):
        if obj.cycle.partner:
            return f"{obj.cycle.partner.first_name} {obj.cycle.partner.last_name}"
        return None
    
    def get_grade(self, obj):
        # Return the most relevant grade
        if obj.blastocyst_grade:
            return obj.blastocyst_grade
        return obj.day3_grade
    
    def get_stage(self, obj):
        # Determine embryo stage from status and development data
        if obj.blastocyst_grade:
            return 'BLASTOCYST'
        elif obj.day3_cell_count:
            return 'CLEAVAGE'
        return obj.status
    
    def get_storage_days(self, obj):
        if obj.frozen_date:
            from django.utils import timezone
            today = timezone.now().date()
            return (today - obj.frozen_date).days
        return 0

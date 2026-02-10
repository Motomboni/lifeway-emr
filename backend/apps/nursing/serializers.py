"""
Serializers for nursing models.

Per EMR Rules:
- Visit-scoped serialization
- Nurse-only creation
- No diagnosis fields
- Immutable records
"""
from rest_framework import serializers
from .models import NursingNote, MedicationAdministration, LabSampleCollection


class NursingNoteSerializer(serializers.ModelSerializer):
    """Serializer for Nursing Notes."""
    recorded_by_name = serializers.CharField(source='recorded_by.get_full_name', read_only=True)
    visit_id = serializers.IntegerField(source='visit.id', read_only=True)
    
    class Meta:
        model = NursingNote
        fields = [
            'id',
            'visit',
            'visit_id',
            'recorded_by',
            'recorded_by_name',
            'note_type',
            'note_content',
            'patient_condition',
            'care_provided',
            'patient_response',
            'recorded_at',
        ]
        read_only_fields = ['id', 'visit', 'recorded_by', 'recorded_at']


class NursingNoteCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating Nursing Notes."""
    
    # Optional field to merge with patient medical history
    merge_with_patient_record = serializers.BooleanField(
        required=False,
        default=False,
        write_only=True,
        help_text="If True, merge this nursing note into patient's medical history"
    )
    
    class Meta:
        model = NursingNote
        fields = [
            'note_type',
            'note_content',
            'patient_condition',
            'care_provided',
            'patient_response',
            'merge_with_patient_record',
        ]


class MedicationAdministrationSerializer(serializers.ModelSerializer):
    """Serializer for Medication Administration."""
    administered_by_name = serializers.CharField(source='administered_by.get_full_name', read_only=True)
    prescription_drug = serializers.CharField(source='prescription.drug', read_only=True)
    prescription_dosage = serializers.CharField(source='prescription.dosage', read_only=True)
    visit_id = serializers.IntegerField(source='visit.id', read_only=True)
    
    class Meta:
        model = MedicationAdministration
        fields = [
            'id',
            'visit',
            'visit_id',
            'prescription',
            'prescription_drug',
            'prescription_dosage',
            'administered_by',
            'administered_by_name',
            'administration_time',
            'dose_administered',
            'route',
            'site',
            'status',
            'administration_notes',
            'reason_if_held',
            'recorded_at',
        ]
        read_only_fields = ['id', 'visit', 'administered_by', 'recorded_at']


class MedicationAdministrationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Medication Administration."""
    
    class Meta:
        model = MedicationAdministration
        fields = [
            'prescription',
            'administration_time',
            'dose_administered',
            'route',
            'site',
            'status',
            'administration_notes',
            'reason_if_held',
        ]


class LabSampleCollectionSerializer(serializers.ModelSerializer):
    """Serializer for Lab Sample Collection."""
    collected_by_name = serializers.CharField(source='collected_by.get_full_name', read_only=True)
    lab_order_tests = serializers.SerializerMethodField()
    visit_id = serializers.IntegerField(source='visit.id', read_only=True)
    
    class Meta:
        model = LabSampleCollection
        fields = [
            'id',
            'visit',
            'visit_id',
            'lab_order',
            'lab_order_tests',
            'collected_by',
            'collected_by_name',
            'collection_time',
            'sample_type',
            'collection_site',
            'status',
            'sample_volume',
            'container_type',
            'collection_notes',
            'reason_if_failed',
            'recorded_at',
        ]
        read_only_fields = ['id', 'visit', 'collected_by', 'recorded_at']
    
    def get_lab_order_tests(self, obj):
        """Get list of tests from lab order."""
        if obj.lab_order and obj.lab_order.tests_requested:
            if isinstance(obj.lab_order.tests_requested, list):
                return obj.lab_order.tests_requested
            return []
        return []


class LabSampleCollectionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating Lab Sample Collection."""
    
    # Optional field to merge with patient medical history
    merge_with_patient_record = serializers.BooleanField(
        required=False,
        default=False,
        write_only=True,
        help_text="If True, merge this lab sample collection into patient's medical history"
    )
    
    class Meta:
        model = LabSampleCollection
        fields = [
            'lab_order',
            'collection_time',
            'sample_type',
            'collection_site',
            'status',
            'sample_volume',
            'container_type',
            'collection_notes',
            'reason_if_failed',
            'merge_with_patient_record',
        ]


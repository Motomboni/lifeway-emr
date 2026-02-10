"""E-Prescription and drug interaction serializers."""
from rest_framework import serializers
from .models import Medication, EPrescription, EPrescriptionItem


class MedicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medication
        fields = ['id', 'name', 'generic_name', 'drug_class', 'contraindications', 'is_active']


class EPrescriptionItemSerializer(serializers.ModelSerializer):
    medication_name = serializers.CharField(source='medication.name', read_only=True)
    medication_id = serializers.IntegerField(source='medication.id', read_only=True)

    class Meta:
        model = EPrescriptionItem
        fields = ['id', 'medication', 'medication_id', 'medication_name', 'dosage', 'frequency', 'duration']


class EPrescriptionSerializer(serializers.ModelSerializer):
    items = EPrescriptionItemSerializer(many=True, read_only=True)
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()

    class Meta:
        model = EPrescription
        fields = [
            'id', 'patient', 'patient_name', 'doctor', 'doctor_name',
            'notes', 'status', 'override_reason', 'items',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_patient_name(self, obj):
        return obj.patient.get_full_name() if obj.patient else None

    def get_doctor_name(self, obj):
        return obj.doctor.get_full_name() if obj.doctor else None


class EPrescriptionCreateSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField()
    medications = serializers.ListField(child=serializers.DictField())
    notes = serializers.CharField(required=False, allow_blank=True)
    override_reason = serializers.CharField(required=False, allow_blank=True)

    def validate_medications(self, value):
        if not value:
            raise serializers.ValidationError("At least one medication is required.")
        for i, m in enumerate(value):
            if not m.get('medication_id'):
                raise serializers.ValidationError("medication_id required for each item.")
        return value


class CheckInteractionsSerializer(serializers.Serializer):
    medication_ids = serializers.ListField(child=serializers.IntegerField(), min_length=1)

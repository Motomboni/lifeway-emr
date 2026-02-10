"""Serializers for insurance policies and claims."""
from rest_framework import serializers
from .insurance_models import ClaimPolicy, Claim, HMOProvider


class ClaimPolicySerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    patient_name = serializers.SerializerMethodField()

    class Meta:
        model = ClaimPolicy
        fields = [
            'id', 'patient', 'patient_name', 'provider', 'provider_name',
            'policy_number', 'coverage_details', 'is_active',
            'created_at', 'updated_at',
        ]

    def get_patient_name(self, obj):
        return obj.patient.get_full_name() if obj.patient else None


class ClaimSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    provider_id = serializers.IntegerField(source='policy.provider_id', read_only=True)
    provider_name = serializers.SerializerMethodField()
    policy_number = serializers.CharField(source='policy.policy_number', read_only=True)

    class Meta:
        model = Claim
        fields = [
            'id', 'patient', 'patient_name', 'policy', 'policy_number',
            'provider_id', 'provider_name',
            'services', 'total_amount', 'status', 'submitted_at', 'response_payload',
            'created_at', 'updated_at',
        ]

    def get_patient_name(self, obj):
        return obj.patient.get_full_name() if obj.patient else None

    def get_provider_name(self, obj):
        return obj.policy.provider.name if obj.policy else None

"""Serializers for structured patient allergies."""

from rest_framework import serializers

from .allergy_models import PatientAllergy


class PatientAllergySerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientAllergy
        fields = [
            "id",
            "patient",
            "allergen",
            "allergen_type",
            "severity",
            "reaction",
            "onset_date",
            "verified",
            "source",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "patient", "created_by", "created_at", "updated_at"]


class PatientAllergyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientAllergy
        fields = [
            "allergen",
            "allergen_type",
            "severity",
            "reaction",
            "onset_date",
            "verified",
            "source",
            "is_active",
        ]

    def validate_allergen(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError("Allergen name is required.")
        return value.strip()

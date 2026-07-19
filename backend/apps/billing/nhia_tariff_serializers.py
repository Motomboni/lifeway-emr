"""Serializers for NHIA tariff API."""

from rest_framework import serializers

from .nhia_tariff_models import NHIATariff


class NHIATariffSerializer(serializers.ModelSerializer):
    class Meta:
        model = NHIATariff
        fields = [
            "id",
            "nhia_code",
            "name",
            "description",
            "category",
            "amount_ngn",
            "icd11_codes",
            "keywords",
            "is_active",
            "effective_from",
        ]
        read_only_fields = fields


class ValidatedCodeSerializer(serializers.Serializer):
    diagnosis = serializers.CharField(allow_blank=True)
    icd11 = serializers.CharField()
    nhia = serializers.CharField()
    icd11_valid = serializers.BooleanField()
    nhia_valid = serializers.BooleanField()
    match_status = serializers.CharField()
    tariff_name = serializers.CharField(allow_null=True)
    amount_ngn = serializers.CharField(allow_null=True)
    category = serializers.CharField(allow_null=True)


class SuggestedTariffSerializer(serializers.Serializer):
    icd11 = serializers.CharField()
    nhia_code = serializers.CharField()
    name = serializers.CharField()
    amount_ngn = serializers.CharField()
    category = serializers.CharField()


class CodeValidationSerializer(serializers.Serializer):
    extracted_codes = serializers.ListField(child=serializers.DictField())
    validated_codes = ValidatedCodeSerializer(many=True)
    unmatched_icd11 = serializers.ListField(child=serializers.CharField())
    unmatched_nhia = serializers.ListField(child=serializers.CharField())
    suggested_tariffs = SuggestedTariffSerializer(many=True)
    all_matched = serializers.BooleanField()

"""
Organization serializers — single-clinic Lifeway (memberships and clinic settings).
"""

from rest_framework import serializers

from apps.guide.guide_modules import DEFAULT_GUIDE_MODULES, normalize_guide_modules

from .models import Organization, OrganizationUser


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer for Organization (read)."""

    guide_modules = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "slug",
            "logo_url",
            "email",
            "phone",
            "address",
            "patient_id_prefix",
            "guide_modules",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_guide_modules(self, obj) -> dict[str, bool]:
        return normalize_guide_modules(getattr(obj, "guide_modules", None))


class OrganizationUpdateSerializer(serializers.ModelSerializer):
    """Clinic admin: update branding, contact, and guide modules (slug read-only)."""

    guide_modules = serializers.DictField(required=False)

    class Meta:
        model = Organization
        fields = [
            "name",
            "logo_url",
            "email",
            "phone",
            "address",
            "patient_id_prefix",
            "guide_modules",
        ]
        extra_kwargs = {
            "name": {"required": False},
            "logo_url": {"required": False, "allow_blank": True},
            "email": {"required": False, "allow_blank": True},
            "phone": {"required": False, "allow_blank": True},
            "address": {"required": False, "allow_blank": True},
            "patient_id_prefix": {"required": False},
        }

    def validate_guide_modules(self, value):
        if value is None:
            return value
        cleaned = {}
        for key in DEFAULT_GUIDE_MODULES:
            if key in value:
                cleaned[key] = bool(value[key])
        return cleaned

    def update(self, instance, validated_data):
        guide_modules_patch = validated_data.pop("guide_modules", None)
        instance = super().update(instance, validated_data)
        if guide_modules_patch is not None:
            merged = normalize_guide_modules(instance.guide_modules)
            merged.update(guide_modules_patch)
            instance.guide_modules = merged
            instance.save(update_fields=["guide_modules", "updated_at"])
        return instance


class OrganizationUserSerializer(serializers.ModelSerializer):
    """Serializer for OrganizationUser with organization details."""

    organization = OrganizationSerializer(read_only=True)

    class Meta:
        model = OrganizationUser
        fields = ["id", "organization", "role", "is_default", "created_at"]
        read_only_fields = fields


class AddMemberSerializer(serializers.Serializer):
    """Serializer for adding a member to an organization."""

    user_id = serializers.IntegerField(
        required=False, help_text="ID of user to add"
    )
    email = serializers.EmailField(
        required=False, help_text="Email of registered staff to add"
    )
    role = serializers.ChoiceField(
        choices=[("ADMIN", "Administrator"), ("MEMBER", "Member")], default="MEMBER"
    )

    def validate(self, attrs):
        if not attrs.get("user_id") and not attrs.get("email"):
            raise serializers.ValidationError(
                "Provide user_id or email of an existing staff account."
            )
        return attrs

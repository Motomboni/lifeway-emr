"""
Organization serializers for SaaS multi-tenancy.
"""

from rest_framework import serializers

from .models import Organization, OrganizationUser, Plan, Subscription


class OrganizationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Organization (admin only)."""

    class Meta:
        model = Organization
        fields = ["name", "slug", "email", "phone", "address", "patient_id_prefix"]
        extra_kwargs = {
            "slug": {"required": True},
            "name": {"required": True},
        }

    def validate_slug(self, value):
        if Organization.objects.filter(slug=value).exists():
            raise serializers.ValidationError(
                "An organization with this slug already exists."
            )
        return value


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer for Organization (read)."""

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
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class OrganizationUpdateSerializer(serializers.ModelSerializer):
    """Clinic admin: update branding and contact (slug read-only)."""

    class Meta:
        model = Organization
        fields = [
            "name",
            "logo_url",
            "email",
            "phone",
            "address",
            "patient_id_prefix",
        ]
        extra_kwargs = {
            "name": {"required": False},
            "logo_url": {"required": False, "allow_blank": True},
            "email": {"required": False, "allow_blank": True},
            "phone": {"required": False, "allow_blank": True},
            "address": {"required": False, "allow_blank": True},
            "patient_id_prefix": {"required": False},
        }


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


class PlanSerializer(serializers.ModelSerializer):
    """Serializer for Plan (read-only for clients)."""

    class Meta:
        model = Plan
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "max_users",
            "max_patients",
            "max_storage_mb",
            "price_monthly",
            "price_yearly",
            "currency",
            "features",
            "is_active",
        ]
        read_only_fields = fields


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for Subscription with plan details."""

    plan = PlanSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "plan",
            "status",
            "current_period_start",
            "current_period_end",
            "trial_ends_at",
            "cancel_at_period_end",
            "cancel_at",
        ]
        read_only_fields = fields


class OrganizationSignupSerializer(serializers.Serializer):
    """Serializer for self-serve organization signup (public)."""

    # Organization
    name = serializers.CharField(max_length=255)
    slug = serializers.SlugField(max_length=100)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    patient_id_prefix = serializers.CharField(
        max_length=10, required=False, allow_blank=True, default="LMC"
    )

    # User (owner)
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=8, write_only=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)

    def validate_slug(self, value):
        if Organization.objects.filter(slug=value).exists():
            raise serializers.ValidationError(
                "An organization with this slug already exists."
            )
        return value

    def validate_username(self, value):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def create(self, validated_data):
        import re

        from django.contrib.auth import get_user_model
        from django.core.exceptions import ValidationError as DjangoValidationError
        from django.db import transaction

        User = get_user_model()

        try:
            with transaction.atomic():
                explicit = (validated_data.get("patient_id_prefix") or "").strip()
                if explicit and explicit.upper() != "LMC":
                    prefix = explicit[:10]
                else:
                    clean = re.sub(r"[^a-z0-9]", "", validated_data["slug"].lower())
                    prefix = (clean[:6].upper() or "ORG")[:10]
                org = Organization.objects.create(
                    name=validated_data["name"],
                    slug=validated_data["slug"],
                    email=validated_data.get("email") or "",
                    phone=validated_data.get("phone") or "",
                    patient_id_prefix=prefix,
                    is_active=True,
                )
                user_email = validated_data.get("email") or ""
                user = User.objects.create_user(
                    username=validated_data["username"],
                    password=validated_data["password"],
                    first_name=validated_data["first_name"],
                    last_name=validated_data["last_name"],
                    email=user_email,
                    role="ADMIN",
                    is_active=True,
                )
                OrganizationUser.objects.create(
                    organization=org,
                    user=user,
                    role="OWNER",
                    is_default=True,
                )
                plan = Plan.objects.filter(slug="starter").first()
                if plan:
                    Subscription.objects.create(
                        organization=org,
                        plan=plan,
                        status="ACTIVE",
                    )
                return {"organization": org, "user": user}
        except DjangoValidationError as e:
            if hasattr(e, 'message_dict'):
                raise serializers.ValidationError(e.message_dict)
            else:
                raise serializers.ValidationError({"error": e.messages})

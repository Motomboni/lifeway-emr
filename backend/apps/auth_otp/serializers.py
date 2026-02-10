"""
OTP Authentication Serializers
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import LoginOTP

User = get_user_model()


class RequestOTPSerializer(serializers.Serializer):
    """
    Serializer for OTP request.
    
    Input: email OR phone + channel
    """
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    channel = serializers.ChoiceField(
        choices=['email', 'sms', 'whatsapp'],
        required=True
    )
    
    def validate(self, attrs):
        """Validate that either email or phone is provided."""
        email = attrs.get('email', '').strip()
        phone = attrs.get('phone', '').strip()
        channel = attrs.get('channel')
        
        # Must provide either email or phone
        if not email and not phone:
            raise serializers.ValidationError(
                "Either email or phone number is required"
            )
        
        # Validate channel matches identifier
        if channel == 'email' and not email:
            raise serializers.ValidationError(
                "Email is required for email channel"
            )
        
        if channel in ['sms', 'whatsapp'] and not phone:
            raise serializers.ValidationError(
                "Phone number is required for SMS/WhatsApp channel"
            )
        
        return attrs


class VerifyOTPSerializer(serializers.Serializer):
    """
    Serializer for OTP verification.
    
    Input: email/phone + otp_code
    Output: JWT tokens + user data
    """
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    otp_code = serializers.CharField(required=True, min_length=6, max_length=6)
    device_type = serializers.ChoiceField(
        choices=['web', 'ios', 'android'],
        required=False,
        default='web'
    )
    
    def validate(self, attrs):
        """Validate input."""
        email = attrs.get('email', '').strip()
        phone = attrs.get('phone', '').strip()
        
        if not email and not phone:
            raise serializers.ValidationError(
                "Either email or phone number is required"
            )
        
        # Validate OTP is numeric
        otp_code = attrs.get('otp_code', '')
        if not otp_code.isdigit():
            raise serializers.ValidationError(
                "OTP must be 6 digits"
            )
        
        return attrs


class RegisterBiometricSerializer(serializers.Serializer):
    """Serializer for biometric registration. User must be authenticated via OTP first."""
    device_id = serializers.CharField(max_length=255, required=True, trim_whitespace=True)
    biometric_token = serializers.CharField(required=True, allow_blank=False)


class BiometricLoginSerializer(serializers.Serializer):
    """Serializer for biometric login."""
    device_id = serializers.CharField(max_length=255, required=True, trim_whitespace=True)
    biometric_token = serializers.CharField(required=True, allow_blank=False)


class PatientPortalUserSerializer(serializers.ModelSerializer):
    """
    Lightweight user serializer for patient portal.
    """
    patient_name = serializers.SerializerMethodField()
    patient_id = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'phone',
            'first_name',
            'last_name',
            'role',
            'patient_name',
            'patient_id',
            'portal_enabled',
            'last_login',
            'biometric_enabled',
        ]
        read_only_fields = fields
    
    def get_patient_name(self, obj):
        """Get patient full name."""
        if obj.patient:
            return obj.patient.get_full_name()
        return None
    
    def get_patient_id(self, obj):
        """Get patient ID."""
        if obj.patient:
            return obj.patient.patient_id
        return None

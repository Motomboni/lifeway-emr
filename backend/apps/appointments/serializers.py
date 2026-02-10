"""
Appointment Serializers - role-based field visibility.

Per EMR Rules:
- Receptionist: Can create/manage all appointments
- Doctor: Can view their own appointments, update status
- Data minimization: Doctors see only their appointments
"""
from rest_framework import serializers
from .models import Appointment
from apps.patients.models import Patient
from apps.visits.models import Visit


class AppointmentSerializer(serializers.ModelSerializer):
    """
    Base serializer for Appointment.
    
    Includes patient and doctor names for display.
    """
    
    patient_name = serializers.SerializerMethodField()
    patient_id = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    cancelled_by_name = serializers.SerializerMethodField()
    
    def get_patient_name(self, obj):
        """Get patient's full name."""
        if obj.patient:
            return obj.patient.get_full_name()
        return None
    
    def get_patient_id(self, obj):
        """Get patient's ID."""
        if obj.patient:
            return obj.patient.patient_id
        return None
    
    def get_doctor_name(self, obj):
        """Get doctor's full name."""
        if obj.doctor:
            return f"{obj.doctor.first_name} {obj.doctor.last_name}".strip()
        return None
    
    def get_created_by_name(self, obj):
        """Get created by user's full name."""
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return None
    
    class Meta:
        model = Appointment
        fields = [
            'id',
            'patient',
            'patient_name',
            'patient_id',
            'doctor',
            'doctor_name',
            'visit',
            'appointment_date',
            'duration_minutes',
            'status',
            'reason',
            'notes',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
            'cancelled_at',
            'cancelled_by',
            'cancelled_by_name',
            'cancellation_reason',
        ]
        read_only_fields = [
            'id',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
            'cancelled_at',
            'cancelled_by',
            'cancelled_by_name',
        ]
    
    def get_cancelled_by_name(self, obj):
        """Get cancelled by user's full name."""
        if obj.cancelled_by:
            return obj.cancelled_by.get_full_name()
        return None


class AppointmentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating appointments (Receptionist and Doctor).
    
    Receptionist or Doctor provides:
    - patient (required)
    - doctor (required)
    - appointment_date (required)
    - duration_minutes (optional, defaults to 30)
    - reason (optional)
    - notes (optional)
    
    System sets:
    - created_by (from authenticated user)
    - status (defaults to SCHEDULED)
    """
    
    class Meta:
        model = Appointment
        fields = [
            'id',
            'patient',
            'doctor',
            'appointment_date',
            'duration_minutes',
            'reason',
            'notes',
        ]
        read_only_fields = ['id']
    
    def validate_doctor(self, value):
        """Ensure doctor has DOCTOR role."""
        user_role = getattr(value, 'role', None)
        if not user_role:
            user_role = getattr(value, 'get_role', lambda: None)()
        
        if user_role != 'DOCTOR':
            raise serializers.ValidationError("Appointment doctor must have DOCTOR role.")
        return value
    
    def validate_appointment_date(self, value):
        """Ensure appointment date is in the future."""
        from django.utils import timezone
        if value <= timezone.now():
            raise serializers.ValidationError("Appointment date must be in the future.")
        return value
    
    def validate(self, attrs):
        """Validate appointment data and check for duplicates."""
        # Check for duplicate appointment (only on create, not update)
        if self.instance is None:
            from core.duplicate_prevention import check_appointment_duplicate
            from django.core.exceptions import ValidationError as DjangoValidationError
            
            patient = attrs.get('patient')
            appointment_date = attrs.get('appointment_date')
            
            if patient and appointment_date:
                try:
                    check_appointment_duplicate(
                        patient=patient,
                        appointment_date=appointment_date
                    )
                except DjangoValidationError as e:
                    raise serializers.ValidationError(str(e))
        
        return attrs
    
    def create(self, validated_data):
        """
        Create appointment with user from context.
        
        Context must provide:
        - request: Django request object (for authenticated user)
        """
        request = self.context['request']
        
        appointment = Appointment.objects.create(
            created_by=request.user,
            **validated_data
        )
        
        return appointment


class AppointmentUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating appointments.
    
    Receptionist can update all fields.
    Doctor can only update status and notes for their own appointments.
    """
    
    class Meta:
        model = Appointment
        fields = [
            'appointment_date',
            'duration_minutes',
            'status',
            'reason',
            'notes',
            'visit',
            'cancellation_reason',
        ]
    
    def validate_appointment_date(self, value):
        """Ensure appointment date is in the future (if changing)."""
        from django.utils import timezone
        if value <= timezone.now():
            raise serializers.ValidationError("Appointment date must be in the future.")
        return value
    
    def validate_status(self, value):
        """Handle status transitions and cancellation."""
        if value == 'CANCELLED' and self.instance.status != 'CANCELLED':
            # Set cancellation timestamp and user
            from django.utils import timezone
            request = self.context.get('request')
            if request and request.user:
                self.instance.cancelled_at = timezone.now()
                self.instance.cancelled_by = request.user
        return value
    
    def update(self, instance, validated_data):
        """Update appointment with validation."""
        # Handle cancellation
        if validated_data.get('status') == 'CANCELLED' and instance.status != 'CANCELLED':
            from django.utils import timezone
            request = self.context.get('request')
            if request and request.user:
                instance.cancelled_at = timezone.now()
                instance.cancelled_by = request.user
        
        return super().update(instance, validated_data)

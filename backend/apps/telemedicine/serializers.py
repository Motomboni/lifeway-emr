"""
Telemedicine Serializers.
"""
from rest_framework import serializers
from .models import TelemedicineSession, TelemedicineParticipant


class TelemedicineParticipantSerializer(serializers.ModelSerializer):
    """Serializer for Telemedicine Participant."""
    
    user_name = serializers.SerializerMethodField()
    user_role = serializers.SerializerMethodField()
    
    class Meta:
        model = TelemedicineParticipant
        fields = [
            'id',
            'user',
            'user_name',
            'user_role',
            'twilio_participant_sid',
            'joined_at',
            'left_at',
            'connection_quality',
            'device_type',
            'browser',
        ]
        read_only_fields = [
            'id',
            'joined_at',
            'left_at',
            'connection_quality',
        ]
    
    def get_user_name(self, obj):
        """Get user's full name."""
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip()
        return None
    
    def get_user_role(self, obj):
        """Get user's role."""
        if obj.user:
            return getattr(obj.user, 'role', None)
        return None


class TelemedicineSessionSerializer(serializers.ModelSerializer):
    """Serializer for Telemedicine Session."""
    
    doctor_name = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    participants = TelemedicineParticipantSerializer(many=True, read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    duration_minutes = serializers.FloatField(read_only=True)
    
    class Meta:
        model = TelemedicineSession
        fields = [
            'id',
            'visit',
            'appointment',
            'twilio_room_sid',
            'twilio_room_name',
            'status',
            'doctor',
            'doctor_name',
            'patient',
            'patient_name',
            'scheduled_start',
            'actual_start',
            'actual_end',
            'duration_seconds',
            'duration_minutes',
            'recording_enabled',
            'recording_sid',
            'recording_url',
            'notes',
            'transcription_status',
            'transcription_text',
            'transcription_requested_at',
            'transcription_completed_at',
            'error_message',
            'created_by',
            'created_at',
            'updated_at',
            'is_active',
            'participants',
        ]
        read_only_fields = [
            'id',
            'twilio_room_sid',
            'twilio_room_name',
            'actual_start',
            'actual_end',
            'duration_seconds',
            'recording_sid',
            'recording_url',
            'transcription_status',
            'transcription_text',
            'transcription_requested_at',
            'transcription_completed_at',
            'error_message',
            'created_by',
            'created_at',
            'updated_at',
        ]
    
    def get_doctor_name(self, obj):
        """Get doctor's full name."""
        if obj.doctor:
            return f"{obj.doctor.first_name} {obj.doctor.last_name}".strip()
        return None
    
    def get_patient_name(self, obj):
        """Get patient's full name."""
        if obj.patient:
            return obj.patient.get_full_name()
        return None


class TelemedicineSessionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a telemedicine session."""
    
    class Meta:
        model = TelemedicineSession
        fields = [
            'visit',
            'appointment',
            'scheduled_start',
            'recording_enabled',
            'notes',
        ]
    
    def validate_visit(self, value):
        """Ensure visit is OPEN."""
        if value.status != 'OPEN':
            raise serializers.ValidationError(
                "Telemedicine sessions can only be created for OPEN visits."
            )
        return value


class CreateSessionSerializer(serializers.Serializer):
    """Serializer for POST /telemedicine/create-session/ – create session from appointment."""
    appointment_id = serializers.IntegerField(help_text="Appointment ID to link")
    recording_enabled = serializers.BooleanField(default=False, required=False)


class TelemedicineTokenSerializer(serializers.Serializer):
    """Serializer for telemedicine access token request."""
    
    session_id = serializers.IntegerField(help_text="Telemedicine session ID")
    
    def validate_session_id(self, value):
        """Ensure session exists and user has access."""
        from .models import TelemedicineSession
        
        try:
            session = TelemedicineSession.objects.get(id=value)
        except TelemedicineSession.DoesNotExist:
            raise serializers.ValidationError("Telemedicine session not found.")
        
        # Store session in context for use in view
        self.context['session'] = session
        return value

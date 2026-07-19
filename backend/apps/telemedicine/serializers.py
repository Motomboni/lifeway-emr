"""
Telemedicine Serializers.
"""

from rest_framework import serializers

from .models import TelemedicineParticipant, TelemedicineSession


class TelemedicineParticipantSerializer(serializers.ModelSerializer):
    """Serializer for Telemedicine Participant."""

    user_name = serializers.SerializerMethodField()
    user_role = serializers.SerializerMethodField()
    invited_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TelemedicineParticipant
        fields = [
            "id",
            "user",
            "user_name",
            "user_role",
            "clinic_role",
            "invite_status",
            "invited_by",
            "invited_by_name",
            "invited_at",
            "invite_message",
            "twilio_participant_sid",
            "joined_at",
            "left_at",
            "connection_quality",
            "device_type",
            "browser",
        ]
        read_only_fields = [
            "id",
            "joined_at",
            "left_at",
            "connection_quality",
            "invited_by",
            "invited_at",
        ]

    def get_user_name(self, obj):
        """Get user's full name."""
        if obj.user:
            return (
                f"{obj.user.first_name} {obj.user.last_name}".strip()
                or obj.user.username
            )
        return None

    def get_user_role(self, obj):
        """Get user's role."""
        if obj.user:
            return getattr(obj.user, "role", None)
        return None

    def get_invited_by_name(self, obj):
        if obj.invited_by:
            name = f"{obj.invited_by.first_name} {obj.invited_by.last_name}".strip()
            return name or obj.invited_by.username
        return None


class TelemedicineInviteSerializer(serializers.Serializer):
    """Invite a staff member into a virtual clinic session."""

    user_id = serializers.IntegerField()
    clinic_role = serializers.ChoiceField(
        choices=["NURSE", "SPECIALIST", "OBSERVER", "STAFF"],
        required=False,
        allow_null=True,
    )
    message = serializers.CharField(
        required=False, allow_blank=True, max_length=255, default=""
    )


class TelemedicineInviteResponseSerializer(serializers.Serializer):
    """Accept or decline a staff invite."""

    accept = serializers.BooleanField()


class TelemedicineSessionSerializer(serializers.ModelSerializer):
    """Serializer for Telemedicine Session."""

    doctor_name = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    participants = TelemedicineParticipantSerializer(many=True, read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    duration_minutes = serializers.FloatField(read_only=True)
    meeting_link = serializers.SerializerMethodField()
    my_invite_status = serializers.SerializerMethodField()
    my_clinic_role = serializers.SerializerMethodField()

    class Meta:
        model = TelemedicineSession
        fields = [
            "id",
            "visit",
            "appointment",
            "twilio_room_sid",
            "twilio_room_name",
            "video_provider",
            "status",
            "doctor",
            "doctor_name",
            "patient",
            "patient_name",
            "scheduled_start",
            "actual_start",
            "actual_end",
            "duration_seconds",
            "duration_minutes",
            "recording_enabled",
            "recording_sid",
            "recording_url",
            "recording_consent_at",
            "notes",
            "transcription_status",
            "transcription_text",
            "transcription_requested_at",
            "transcription_completed_at",
            "error_message",
            "created_by",
            "created_at",
            "updated_at",
            "is_active",
            "participants",
            "meeting_link",
            "my_invite_status",
            "my_clinic_role",
        ]
        read_only_fields = [
            "id",
            "twilio_room_sid",
            "twilio_room_name",
            "video_provider",
            "actual_start",
            "actual_end",
            "duration_seconds",
            "recording_sid",
            "recording_url",
            "transcription_status",
            "transcription_text",
            "transcription_requested_at",
            "transcription_completed_at",
            "error_message",
            "created_by",
            "created_at",
            "updated_at",
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

    def get_meeting_link(self, obj):
        from .notifications import build_meeting_link

        return build_meeting_link(obj.id)

    def get_my_invite_status(self, obj):
        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return None
        from .access import is_session_host, is_session_patient

        if is_session_host(request.user, obj):
            return "ACCEPTED"
        if is_session_patient(request.user, obj):
            return "ACCEPTED"
        for p in obj.participants.all():
            if p.user_id == request.user.id:
                return p.invite_status
        return None

    def get_my_clinic_role(self, obj):
        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return None
        from .access import is_session_host, is_session_patient

        if is_session_host(request.user, obj):
            return "HOST"
        if is_session_patient(request.user, obj):
            return "PATIENT"
        for p in obj.participants.all():
            if p.user_id == request.user.id:
                return p.clinic_role
        return None


class TelemedicineSessionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a telemedicine session."""

    recording_consent_acknowledged = serializers.BooleanField(
        required=False,
        default=False,
        write_only=True,
        help_text="Required when recording_enabled is true.",
    )

    class Meta:
        model = TelemedicineSession
        fields = [
            "visit",
            "appointment",
            "scheduled_start",
            "recording_enabled",
            "recording_consent_acknowledged",
            "notes",
        ]

    def validate_visit(self, value):
        """Ensure visit is OPEN."""
        if value.status != "OPEN":
            raise serializers.ValidationError(
                "Telemedicine sessions can only be created for OPEN visits."
            )
        return value

    def validate(self, attrs):
        if attrs.get("recording_enabled") and not attrs.get(
            "recording_consent_acknowledged"
        ):
            raise serializers.ValidationError(
                {
                    "recording_consent_acknowledged": [
                        "Patient recording consent is required when recording is enabled."
                    ]
                }
            )
        return attrs


class CreateSessionSerializer(serializers.Serializer):
    """Serializer for POST /telemedicine/create-session/ – create session from appointment."""

    appointment_id = serializers.IntegerField(help_text="Appointment ID to link")
    recording_enabled = serializers.BooleanField(default=False, required=False)
    recording_consent_acknowledged = serializers.BooleanField(
        default=False, required=False
    )

    def validate(self, attrs):
        if attrs.get("recording_enabled") and not attrs.get(
            "recording_consent_acknowledged"
        ):
            raise serializers.ValidationError(
                {
                    "recording_consent_acknowledged": [
                        "Patient recording consent is required when recording is enabled."
                    ]
                }
            )
        return attrs


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
        self.context["session"] = session
        return value

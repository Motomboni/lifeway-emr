"""
Telemedicine models - for tracking video consultation sessions.

Per EMR Rules:
- Telemedicine sessions must be visit-scoped
- All sessions must be audited
- PHI data must be protected
- Session recordings (if enabled) must be encrypted
"""
from django.db import models
from django.utils import timezone


class TelemedicineSession(models.Model):
    """
    Telemedicine Session model - tracks video consultation sessions.
    
    Design Principles:
    1. Visit-scoped: All sessions linked to a visit
    2. Twilio Room ID stored for tracking
    3. Session metadata tracked
    4. Audit logging mandatory
    """
    
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('FAILED', 'Failed'),
    ]
    
    # Session information
    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.PROTECT,
        related_name='telemedicine_sessions',
        help_text="Visit this telemedicine session belongs to"
    )
    
    appointment = models.ForeignKey(
        'appointments.Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='telemedicine_sessions',
        help_text="Related appointment (if applicable)"
    )
    
    # Twilio Room information
    twilio_room_sid = models.CharField(
        max_length=255,
        unique=True,
        help_text="Twilio Room SID"
    )
    
    twilio_room_name = models.CharField(
        max_length=255,
        help_text="Twilio Room Name"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='SCHEDULED',
        help_text="Status of the telemedicine session"
    )
    
    # Participants
    doctor = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='telemedicine_sessions_as_doctor',
        help_text="Doctor participating in the session"
    )
    
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.PROTECT,
        related_name='telemedicine_sessions',
        help_text="Patient participating in the session"
    )
    
    # Session metadata
    scheduled_start = models.DateTimeField(
        help_text="Scheduled start time"
    )
    
    actual_start = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Actual start time"
    )
    
    actual_end = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Actual end time"
    )
    
    duration_seconds = models.IntegerField(
        null=True,
        blank=True,
        help_text="Session duration in seconds"
    )
    
    # Recording information (if enabled)
    recording_enabled = models.BooleanField(
        default=False,
        help_text="Whether session recording is enabled"
    )
    
    recording_sid = models.CharField(
        max_length=255,
        blank=True,
        help_text="Twilio Recording SID (if recording exists)"
    )
    
    recording_url = models.URLField(
        blank=True,
        help_text="URL to access recording (if available)"
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        help_text="Session notes or summary"
    )
    
    # Transcription (from recording, after session)
    TRANSCRIPTION_STATUS_CHOICES = [
        ('', 'Not requested'),
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    transcription_status = models.CharField(
        max_length=20,
        choices=TRANSCRIPTION_STATUS_CHOICES,
        default='',
        blank=True,
        help_text="Status of automatic transcription"
    )
    transcription_text = models.TextField(
        blank=True,
        help_text="Transcribed text from session recording (when available)"
    )
    transcription_requested_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When transcription was requested"
    )
    transcription_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When transcription finished"
    )
    
    # Error tracking
    error_message = models.TextField(
        blank=True,
        help_text="Error message if session failed"
    )
    
    # User tracking
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='telemedicine_sessions_created',
        help_text="User who created this session"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the session was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the session was last updated"
    )
    
    class Meta:
        db_table = 'telemedicine_sessions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['visit']),
            models.Index(fields=['status']),
            models.Index(fields=['twilio_room_sid']),
            models.Index(fields=['scheduled_start']),
        ]
        verbose_name = 'Telemedicine Session'
        verbose_name_plural = 'Telemedicine Sessions'
    
    def __str__(self):
        return f"Telemedicine Session {self.id} - {self.visit.id} ({self.status})"
    
    @property
    def is_active(self):
        """Check if session is currently active."""
        return self.status == 'IN_PROGRESS'
    
    @property
    def duration_minutes(self):
        """Get duration in minutes."""
        if self.duration_seconds:
            return round(self.duration_seconds / 60, 2)
        return None


class TelemedicineParticipant(models.Model):
    """
    Telemedicine Participant model - tracks participants in a session.
    
    Design Principles:
    1. Links users to sessions
    2. Tracks join/leave times
    3. Tracks connection quality
    """
    
    session = models.ForeignKey(
        'telemedicine.TelemedicineSession',
        on_delete=models.CASCADE,
        related_name='participants',
        help_text="Telemedicine session"
    )
    
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='telemedicine_participations',
        help_text="User participating in the session"
    )
    
    # Twilio participant information
    twilio_participant_sid = models.CharField(
        max_length=255,
        blank=True,
        help_text="Twilio Participant SID"
    )
    
    # Connection tracking
    joined_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When participant joined"
    )
    
    left_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When participant left"
    )
    
    connection_quality = models.CharField(
        max_length=50,
        blank=True,
        help_text="Connection quality (good, fair, poor)"
    )
    
    # Device information
    device_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Device type (desktop, mobile, tablet)"
    )
    
    browser = models.CharField(
        max_length=100,
        blank=True,
        help_text="Browser name and version"
    )
    
    class Meta:
        db_table = 'telemedicine_participants'
        unique_together = ['session', 'user']
        indexes = [
            models.Index(fields=['session']),
            models.Index(fields=['user']),
        ]
        verbose_name = 'Telemedicine Participant'
        verbose_name_plural = 'Telemedicine Participants'
    
    def __str__(self):
        return f"Participant {self.user.username} in Session {self.session.id}"

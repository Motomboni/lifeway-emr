"""
Django Admin for Telemedicine models.
"""
from django.contrib import admin
from .models import TelemedicineSession, TelemedicineParticipant


@admin.register(TelemedicineSession)
class TelemedicineSessionAdmin(admin.ModelAdmin):
    """Admin interface for TelemedicineSession model."""
    
    list_display = [
        'id',
        'visit',
        'doctor',
        'patient',
        'status',
        'scheduled_start',
        'actual_start',
        'duration_minutes',
        'recording_enabled',
        'created_at',
    ]
    
    list_filter = [
        'status',
        'recording_enabled',
        'created_at',
        'scheduled_start',
    ]
    
    search_fields = [
        'id',
        'visit__id',
        'doctor__username',
        'doctor__email',
        'patient__first_name',
        'patient__last_name',
        'twilio_room_sid',
        'twilio_room_name',
    ]
    
    readonly_fields = [
        'id',
        'twilio_room_sid',
        'twilio_room_name',
        'actual_start',
        'actual_end',
        'duration_seconds',
        'recording_sid',
        'recording_url',
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('Session Information', {
            'fields': (
                'id',
                'visit',
                'appointment',
                'status',
            )
        }),
        ('Twilio Information', {
            'fields': (
                'twilio_room_sid',
                'twilio_room_name',
            )
        }),
        ('Participants', {
            'fields': (
                'doctor',
                'patient',
            )
        }),
        ('Timing', {
            'fields': (
                'scheduled_start',
                'actual_start',
                'actual_end',
                'duration_seconds',
            )
        }),
        ('Recording', {
            'fields': (
                'recording_enabled',
                'recording_sid',
                'recording_url',
            )
        }),
        ('Metadata', {
            'fields': (
                'notes',
                'error_message',
                'created_by',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            )
        }),
    )


@admin.register(TelemedicineParticipant)
class TelemedicineParticipantAdmin(admin.ModelAdmin):
    """Admin interface for TelemedicineParticipant model."""
    
    list_display = [
        'id',
        'session',
        'user',
        'joined_at',
        'left_at',
        'connection_quality',
    ]
    
    list_filter = [
        'connection_quality',
        'device_type',
        'joined_at',
    ]
    
    search_fields = [
        'session__id',
        'user__username',
        'user__email',
    ]
    
    readonly_fields = [
        'id',
        'joined_at',
        'left_at',
    ]

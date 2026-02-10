"""
Django Admin for Backup models.
"""
from django.contrib import admin
from .models import Backup, Restore


@admin.register(Backup)
class BackupAdmin(admin.ModelAdmin):
    """Admin interface for Backup model."""
    
    list_display = [
        'id',
        'backup_type',
        'status',
        'file_size',
        'created_by',
        'created_at',
        'completed_at',
        'is_expired',
    ]
    
    list_filter = [
        'backup_type',
        'status',
        'is_encrypted',
        'created_at',
        'expires_at',
    ]
    
    search_fields = [
        'id',
        'description',
        'created_by__username',
        'created_by__email',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'started_at',
        'completed_at',
        'duration',
        'is_expired',
    ]
    
    fieldsets = (
        ('Backup Information', {
            'fields': (
                'id',
                'backup_type',
                'status',
                'file_path',
                'file_size',
                'is_encrypted',
                'encryption_key_id',
            )
        }),
        ('Backup Scope', {
            'fields': (
                'includes_patients',
                'includes_visits',
                'includes_consultations',
                'includes_lab_data',
                'includes_radiology_data',
                'includes_prescriptions',
                'includes_audit_logs',
            )
        }),
        ('Metadata', {
            'fields': (
                'description',
                'error_message',
                'created_by',
                'expires_at',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'started_at',
                'completed_at',
                'duration',
                'is_expired',
            )
        }),
    )


@admin.register(Restore)
class RestoreAdmin(admin.ModelAdmin):
    """Admin interface for Restore model."""
    
    list_display = [
        'id',
        'backup',
        'status',
        'created_by',
        'created_at',
        'started_at',
        'completed_at',
    ]
    
    list_filter = [
        'status',
        'created_at',
        'backup',
    ]
    
    search_fields = [
        'id',
        'description',
        'backup__id',
        'created_by__username',
        'created_by__email',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'started_at',
        'completed_at',
        'duration',
    ]
    
    fieldsets = (
        ('Restore Information', {
            'fields': (
                'id',
                'backup',
                'status',
            )
        }),
        ('Restore Scope', {
            'fields': (
                'restore_patients',
                'restore_visits',
                'restore_consultations',
                'restore_lab_data',
                'restore_radiology_data',
                'restore_prescriptions',
                'restore_audit_logs',
            )
        }),
        ('Metadata', {
            'fields': (
                'description',
                'error_message',
                'created_by',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'started_at',
                'completed_at',
                'duration',
            )
        }),
    )

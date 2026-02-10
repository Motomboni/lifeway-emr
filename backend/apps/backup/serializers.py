"""
Backup and Restore Serializers.
"""
from rest_framework import serializers
from .models import Backup, Restore


class BackupSerializer(serializers.ModelSerializer):
    """
    Serializer for Backup.
    """
    created_by_name = serializers.SerializerMethodField()
    duration_seconds = serializers.SerializerMethodField()
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Backup
        fields = [
            'id',
            'backup_type',
            'status',
            'file_path',
            'file_size',
            'is_encrypted',
            'encryption_key_id',
            'includes_patients',
            'includes_visits',
            'includes_consultations',
            'includes_lab_data',
            'includes_radiology_data',
            'includes_prescriptions',
            'includes_audit_logs',
            'description',
            'error_message',
            'created_by',
            'created_by_name',
            'started_at',
            'completed_at',
            'created_at',
            'expires_at',
            'duration_seconds',
            'is_expired',
        ]
        read_only_fields = [
            'id',
            'status',
            'file_path',
            'file_size',
            'started_at',
            'completed_at',
            'error_message',
            'created_by',
            'created_by_name',
            'created_at',
            'duration_seconds',
            'is_expired',
        ]
    
    def get_created_by_name(self, obj):
        """Get created by user's full name."""
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return None
    
    def get_duration_seconds(self, obj):
        """Get backup duration in seconds."""
        duration = obj.duration
        if duration:
            return duration.total_seconds()
        return None


class BackupCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating backups.
    """
    
    class Meta:
        model = Backup
        fields = [
            'backup_type',
            'includes_patients',
            'includes_visits',
            'includes_consultations',
            'includes_lab_data',
            'includes_radiology_data',
            'includes_prescriptions',
            'includes_audit_logs',
            'description',
            'expires_at',
        ]


class RestoreSerializer(serializers.ModelSerializer):
    """
    Serializer for Restore.
    """
    created_by_name = serializers.SerializerMethodField()
    duration_seconds = serializers.SerializerMethodField()
    backup_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Restore
        fields = [
            'id',
            'backup',
            'backup_info',
            'status',
            'restore_patients',
            'restore_visits',
            'restore_consultations',
            'restore_lab_data',
            'restore_radiology_data',
            'restore_prescriptions',
            'restore_audit_logs',
            'description',
            'error_message',
            'created_by',
            'created_by_name',
            'started_at',
            'completed_at',
            'created_at',
            'duration_seconds',
        ]
        read_only_fields = [
            'id',
            'status',
            'started_at',
            'completed_at',
            'error_message',
            'created_by',
            'created_by_name',
            'created_at',
            'duration_seconds',
        ]
    
    def get_created_by_name(self, obj):
        """Get created by user's full name."""
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return None
    
    def get_duration_seconds(self, obj):
        """Get restore duration in seconds."""
        duration = obj.duration
        if duration:
            return duration.total_seconds()
        return None
    
    def get_backup_info(self, obj):
        """Get backup information."""
        if obj.backup:
            return {
                'id': obj.backup.id,
                'backup_type': obj.backup.backup_type,
                'created_at': obj.backup.created_at,
                'file_size': obj.backup.file_size,
            }
        return None


class RestoreCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating restore operations.
    """
    
    class Meta:
        model = Restore
        fields = [
            'backup',
            'restore_patients',
            'restore_visits',
            'restore_consultations',
            'restore_lab_data',
            'restore_radiology_data',
            'restore_prescriptions',
            'restore_audit_logs',
            'description',
        ]
    
    def validate_backup(self, value):
        """Ensure backup is completed and not expired."""
        if value.status != 'COMPLETED':
            raise serializers.ValidationError("Can only restore from completed backups.")
        if value.is_expired:
            raise serializers.ValidationError("Cannot restore from expired backup.")
        return value

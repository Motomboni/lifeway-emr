"""
Backup models - for tracking backup and restore operations.

Per EMR Rules:
- Backups must be encrypted
- Backup metadata tracked for compliance
- Restore operations must be audited
- Only authorized users can perform backups/restores
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class Backup(models.Model):
    """
    Backup model - tracks backup operations.
    
    Design Principles:
    1. Tracks backup metadata (not the actual backup data)
    2. Backup files stored externally (S3, local filesystem, etc.)
    3. Encryption status tracked
    4. Audit logging mandatory
    """
    
    BACKUP_TYPES = [
        ('FULL', 'Full Backup'),
        ('INCREMENTAL', 'Incremental Backup'),
        ('DIFFERENTIAL', 'Differential Backup'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    # Backup information
    backup_type = models.CharField(
        max_length=20,
        choices=BACKUP_TYPES,
        default='FULL',
        help_text="Type of backup"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text="Status of the backup operation"
    )
    
    # File information
    file_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Path to backup file (relative or absolute)"
    )
    
    file_size = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Size of backup file in bytes"
    )
    
    is_encrypted = models.BooleanField(
        default=True,
        help_text="Whether the backup is encrypted"
    )
    
    encryption_key_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Identifier for encryption key (not the key itself)"
    )
    
    # Backup scope
    includes_patients = models.BooleanField(
        default=True,
        help_text="Whether backup includes patient data"
    )
    
    includes_visits = models.BooleanField(
        default=True,
        help_text="Whether backup includes visit data"
    )
    
    includes_consultations = models.BooleanField(
        default=True,
        help_text="Whether backup includes consultation data"
    )
    
    includes_lab_data = models.BooleanField(
        default=True,
        help_text="Whether backup includes lab data"
    )
    
    includes_radiology_data = models.BooleanField(
        default=True,
        help_text="Whether backup includes radiology data"
    )
    
    includes_prescriptions = models.BooleanField(
        default=True,
        help_text="Whether backup includes prescription data"
    )
    
    includes_audit_logs = models.BooleanField(
        default=True,
        help_text="Whether backup includes audit logs"
    )
    
    # Metadata
    description = models.TextField(
        blank=True,
        help_text="Description or notes about this backup"
    )
    
    error_message = models.TextField(
        blank=True,
        help_text="Error message if backup failed"
    )
    
    # User tracking
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='backups_created',
        help_text="User who initiated this backup"
    )
    
    # Timestamps
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the backup started"
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the backup completed"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the backup record was created"
    )
    
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this backup expires (for retention policies)"
    )
    
    class Meta:
        db_table = 'backups'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['backup_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['created_by']),
        ]
        verbose_name = 'Backup'
        verbose_name_plural = 'Backups'
    
    def __str__(self):
        return f"Backup {self.id} - {self.backup_type} ({self.status})"
    
    @property
    def duration(self):
        """Calculate backup duration."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    @property
    def is_expired(self):
        """Check if backup has expired."""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False


class Restore(models.Model):
    """
    Restore model - tracks restore operations.
    
    Design Principles:
    1. Tracks restore metadata
    2. Links to source backup
    3. Audit logging mandatory
    4. Only authorized users can restore
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    # Restore information
    backup = models.ForeignKey(
        'backup.Backup',
        on_delete=models.PROTECT,
        related_name='restores',
        help_text="Backup being restored"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text="Status of the restore operation"
    )
    
    # Restore scope
    restore_patients = models.BooleanField(
        default=True,
        help_text="Whether to restore patient data"
    )
    
    restore_visits = models.BooleanField(
        default=True,
        help_text="Whether to restore visit data"
    )
    
    restore_consultations = models.BooleanField(
        default=True,
        help_text="Whether to restore consultation data"
    )
    
    restore_lab_data = models.BooleanField(
        default=True,
        help_text="Whether to restore lab data"
    )
    
    restore_radiology_data = models.BooleanField(
        default=True,
        help_text="Whether to restore radiology data"
    )
    
    restore_prescriptions = models.BooleanField(
        default=True,
        help_text="Whether to restore prescription data"
    )
    
    restore_audit_logs = models.BooleanField(
        default=False,
        help_text="Whether to restore audit logs (usually False to preserve current audit trail)"
    )
    
    # Metadata
    description = models.TextField(
        blank=True,
        help_text="Description or notes about this restore"
    )
    
    error_message = models.TextField(
        blank=True,
        help_text="Error message if restore failed"
    )
    
    # User tracking
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='restores_created',
        help_text="User who initiated this restore"
    )
    
    # Timestamps
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the restore started"
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the restore completed"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the restore record was created"
    )
    
    class Meta:
        db_table = 'restores'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['backup']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['created_by']),
        ]
        verbose_name = 'Restore'
        verbose_name_plural = 'Restores'
    
    def __str__(self):
        return f"Restore {self.id} from Backup {self.backup_id} ({self.status})"
    
    @property
    def duration(self):
        """Calculate restore duration."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    def clean(self):
        """Validation: Ensure backup exists and is completed."""
        if self.backup_id:
            if self.backup.status != 'COMPLETED':
                raise ValidationError("Can only restore from completed backups.")
            if self.backup.is_expired:
                raise ValidationError("Cannot restore from expired backup.")

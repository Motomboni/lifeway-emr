"""
Image Upload Session Models for Offline-First Imaging Upload System.

This module provides session-based tracking for offline image uploads,
ensuring data integrity, retry safety, and preventing orphan images.
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid
import hashlib


class ImageUploadSession(models.Model):
    """
    Session for tracking offline image uploads.
    
    A session represents a single image upload attempt with:
    - Local storage with UUID
    - Metadata queued separately from binaries
    - Checksum verification
    - Retry-safe, resumable uploads
    - Server ACK required before local deletion
    """
    
    STATUS_CHOICES = [
        ('QUEUED', 'Queued'),
        ('METADATA_UPLOADING', 'Metadata Uploading'),
        ('METADATA_UPLOADED', 'Metadata Uploaded'),
        ('BINARY_UPLOADING', 'Binary Uploading'),
        ('SYNCED', 'Synced'),
        ('ACK_RECEIVED', 'Acknowledged'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    # Session identification
    session_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
        help_text="Unique session identifier for this upload"
    )
    
    # Radiology order reference
    radiology_order = models.ForeignKey(
        'radiology.RadiologyRequest',
        on_delete=models.CASCADE,
        related_name='image_upload_sessions',
        help_text="Radiology order this image belongs to"
    )
    
    # Local file information
    local_file_path = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Local file path where image is stored temporarily"
    )
    
    local_file_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
        help_text="UUID for local file identification"
    )
    
    file_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Original filename"
    )
    
    file_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="File size in bytes"
    )
    
    content_type = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="MIME type (e.g., image/jpeg, image/dicom)"
    )
    
    # Checksum for integrity verification
    checksum = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="SHA-256 checksum of the image file"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='QUEUED',
        db_index=True,
        help_text="Current upload status"
    )
    
    # Upload progress
    bytes_uploaded = models.PositiveIntegerField(
        default=0,
        help_text="Number of bytes uploaded so far"
    )
    
    upload_progress_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Upload progress percentage (0-100)"
    )
    
    # Retry tracking
    retry_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of retry attempts"
    )
    
    max_retries = models.PositiveIntegerField(
        default=5,
        help_text="Maximum number of retry attempts"
    )
    
    last_retry_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last retry attempt"
    )
    
    # Error tracking
    error_message = models.TextField(
        blank=True,
        help_text="Error message if upload failed"
    )
    
    error_code = models.CharField(
        max_length=50,
        blank=True,
        help_text="Error code for programmatic handling"
    )
    
    # Server acknowledgment
    server_ack_received = models.BooleanField(
        default=False,
        help_text="Whether server has acknowledged successful upload"
    )
    
    server_ack_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when server acknowledgment was received"
    )
    
    server_image_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="ID of the image record on the server after successful upload"
    )
    
    # Metadata upload tracking
    metadata_uploaded = models.BooleanField(
        default=False,
        help_text="Whether metadata has been uploaded to server"
    )
    
    metadata_uploaded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when metadata was uploaded"
    )
    
    # Binary upload tracking
    binary_uploaded = models.BooleanField(
        default=False,
        help_text="Whether binary data has been uploaded to server"
    )
    
    binary_uploaded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when binary data was uploaded"
    )
    
    # Audit trail
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='image_upload_sessions',
        help_text="User who initiated the upload"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the upload session was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the upload session was last updated"
    )
    
    # Additional metadata (JSON field for flexibility)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata about the image"
    )
    
    class Meta:
        db_table = 'image_upload_sessions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['local_file_uuid']),
            models.Index(fields=['status']),
            models.Index(fields=['radiology_order', 'status']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'Image Upload Session'
        verbose_name_plural = 'Image Upload Sessions'
    
    def __str__(self):
        return f"Upload Session {self.session_id} - {self.file_name} ({self.status})"
    
    def clean(self):
        """Validate upload session."""
        errors = {}
        
        # Validate status transitions
        if self.pk:
            old_instance = ImageUploadSession.objects.get(pk=self.pk)
            old_status = old_instance.status
            
            # Define valid status transitions
            valid_transitions = {
                'QUEUED': ['METADATA_UPLOADING', 'CANCELLED', 'FAILED'],
                'METADATA_UPLOADING': ['METADATA_UPLOADED', 'FAILED', 'QUEUED'],
                'METADATA_UPLOADED': ['BINARY_UPLOADING', 'FAILED'],
                'BINARY_UPLOADING': ['SYNCED', 'FAILED', 'BINARY_UPLOADING'],
                'SYNCED': ['ACK_RECEIVED', 'FAILED'],
                'ACK_RECEIVED': [],  # Terminal state
                'FAILED': ['QUEUED'],  # Can retry
                'CANCELLED': [],  # Terminal state
            }
            
            if old_status in valid_transitions:
                if self.status not in valid_transitions[old_status]:
                    errors['status'] = (
                        f"Invalid status transition from {old_status} to {self.status}. "
                        f"Valid transitions: {', '.join(valid_transitions[old_status])}"
                    )
        
        # Validate checksum format (SHA-256 is 64 hex characters)
        if self.checksum:
            if len(self.checksum) != 64:
                errors['checksum'] = "Checksum must be a valid SHA-256 hash (64 hex characters)."
        elif not self.pk:  # Require checksum for new sessions
            errors['checksum'] = "Checksum is required for new upload sessions."
        
        # Validate file size
        if self.file_size is not None and self.file_size <= 0:
            errors['file_size'] = "File size must be greater than 0."
        elif not self.pk and not self.file_size:  # Require file_size for new sessions
            errors['file_size'] = "File size is required for new upload sessions."
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Override save to update progress and validate."""
        # Update progress percentage
        if self.file_size > 0:
            self.upload_progress_percent = (self.bytes_uploaded / self.file_size) * 100
        
        # Update timestamps based on status
        if self.status == 'METADATA_UPLOADED' and not self.metadata_uploaded:
            self.metadata_uploaded = True
            self.metadata_uploaded_at = timezone.now()
        
        if self.status == 'SYNCED' and not self.binary_uploaded:
            self.binary_uploaded = True
            self.binary_uploaded_at = timezone.now()
        
        if self.status == 'ACK_RECEIVED' and not self.server_ack_received:
            self.server_ack_received = True
            self.server_ack_at = timezone.now()
        
        self.full_clean()
        super().save(*args, **kwargs)
    
    def can_retry(self) -> bool:
        """Check if this session can be retried."""
        return (
            self.status == 'FAILED' and
            self.retry_count < self.max_retries
        )
    
    def mark_as_queued(self):
        """Mark session as queued for retry."""
        if not self.can_retry():
            raise ValidationError("Session cannot be retried.")
        self.status = 'QUEUED'
        self.last_retry_at = timezone.now()
        self.retry_count += 1
        self.error_message = ''
        self.error_code = ''
        self.save()
    
    def mark_metadata_uploading(self):
        """Mark metadata as being uploaded."""
        self.status = 'METADATA_UPLOADING'
        self.save()
    
    def mark_metadata_uploaded(self):
        """Mark metadata as uploaded."""
        self.status = 'METADATA_UPLOADED'
        self.metadata_uploaded = True
        self.metadata_uploaded_at = timezone.now()
        self.save()
    
    def mark_binary_uploading(self, bytes_uploaded: int = 0):
        """Mark binary as being uploaded."""
        self.status = 'BINARY_UPLOADING'
        self.bytes_uploaded = bytes_uploaded
        self.save()
    
    def mark_synced(self):
        """Mark binary as synced to server."""
        self.status = 'SYNCED'
        self.binary_uploaded = True
        self.binary_uploaded_at = timezone.now()
        self.bytes_uploaded = self.file_size
        self.upload_progress_percent = 100
        self.save()
    
    def mark_ack_received(self, server_image_id: int):
        """Mark server acknowledgment as received."""
        self.status = 'ACK_RECEIVED'
        self.server_ack_received = True
        self.server_ack_at = timezone.now()
        self.server_image_id = server_image_id
        self.save()
    
    def mark_failed(self, error_message: str, error_code: str = ''):
        """Mark upload as failed."""
        self.status = 'FAILED'
        self.error_message = error_message
        self.error_code = error_code
        self.save()
    
    def mark_cancelled(self):
        """Mark upload as cancelled."""
        self.status = 'CANCELLED'
        self.save()
    
    def is_complete(self) -> bool:
        """Check if upload is complete (ACK received)."""
        return self.status == 'ACK_RECEIVED'
    
    def is_safe_to_delete_local(self) -> bool:
        """Check if local file can be safely deleted."""
        return self.is_complete() and self.server_ack_received
    
    @staticmethod
    def calculate_checksum(file_path: str) -> str:
        """Calculate SHA-256 checksum of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def verify_checksum(self, file_path: str) -> bool:
        """Verify file checksum matches stored checksum."""
        calculated = self.calculate_checksum(file_path)
        return calculated == self.checksum


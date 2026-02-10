"""
Image Upload Session Models for Offline-First Imaging Upload.

This module provides session-based tracking for offline image uploads,
ensuring data integrity, retry safety, and proper cleanup.
"""
import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class ImageUploadSession(models.Model):
    """
    Session for tracking offline image uploads.
    
    A session can contain multiple images and tracks the overall
    upload progress. This ensures:
    - No orphan images
    - Proper retry handling
    - Full audit trail
    """
    
    STATUS_CHOICES = [
        ('QUEUED', 'Queued - Ready to upload'),
        ('UPLOADING', 'Uploading - Currently syncing'),
        ('SYNCED', 'Synced - All images uploaded and ACK received'),
        ('FAILED', 'Failed - Requires manual intervention'),
        ('PARTIAL', 'Partial - Some images failed'),
    ]
    
    # Unique session identifier (generated client-side)
    session_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
        help_text="Unique identifier for this upload session"
    )
    
    # Link to radiology order
    radiology_order = models.ForeignKey(
        'radiology.RadiologyOrder',
        on_delete=models.CASCADE,
        related_name='upload_sessions',
        help_text="Radiology order this session belongs to"
    )
    
    # Session metadata
    device_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Device identifier (for tracking which device uploaded)"
    )
    
    device_info = models.JSONField(
        default=dict,
        blank=True,
        help_text="Device information (OS, browser, etc.)"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='QUEUED',
        db_index=True,
        help_text="Current status of the upload session"
    )
    
    # Progress tracking
    total_images = models.PositiveIntegerField(
        default=0,
        help_text="Total number of images in this session"
    )
    
    images_uploaded = models.PositiveIntegerField(
        default=0,
        help_text="Number of images successfully uploaded"
    )
    
    images_failed = models.PositiveIntegerField(
        default=0,
        help_text="Number of images that failed to upload"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the session was created"
    )
    
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the upload started"
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the upload completed (successfully or failed)"
    )
    
    # Error tracking
    error_message = models.TextField(
        blank=True,
        help_text="Error message if upload failed"
    )
    
    # Audit trail
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='upload_sessions',
        help_text="User who created this session"
    )
    
    class Meta:
        db_table = 'image_upload_sessions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session_uuid']),
            models.Index(fields=['radiology_order', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
        verbose_name = 'Image Upload Session'
        verbose_name_plural = 'Image Upload Sessions'
    
    def __str__(self):
        return f"Upload Session {self.session_uuid} - {self.get_status_display()}"
    
    def clean(self):
        """Validate session."""
        errors = {}
        
        # Validate progress counts
        if self.images_uploaded + self.images_failed > self.total_images:
            errors['images_uploaded'] = "Uploaded + failed images cannot exceed total images."
        
        if errors:
            raise ValidationError(errors)
    
    def mark_started(self):
        """Mark session as started."""
        if self.status == 'QUEUED':
            self.status = 'UPLOADING'
            self.started_at = timezone.now()
            self.save(update_fields=['status', 'started_at'])
    
    def mark_image_uploaded(self):
        """Increment uploaded count."""
        self.images_uploaded += 1
        self._update_status()
        self.save(update_fields=['images_uploaded', 'status', 'completed_at'])
    
    def mark_image_failed(self):
        """Increment failed count."""
        self.images_failed += 1
        self._update_status()
        self.save(update_fields=['images_failed', 'status', 'completed_at'])
    
    def mark_failed(self, error_message: str = ''):
        """Mark session as failed."""
        self.status = 'FAILED'
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.save(update_fields=['status', 'completed_at', 'error_message'])
    
    def _update_status(self):
        """Update status based on progress."""
        if self.images_uploaded + self.images_failed >= self.total_images:
            if self.images_failed == 0:
                self.status = 'SYNCED'
            elif self.images_uploaded > 0:
                self.status = 'PARTIAL'
            else:
                self.status = 'FAILED'
            self.completed_at = timezone.now()
        elif self.status == 'QUEUED':
            self.status = 'UPLOADING'
            if not self.started_at:
                self.started_at = timezone.now()
    
    def get_progress_percentage(self) -> float:
        """Get upload progress as percentage."""
        if self.total_images == 0:
            return 0.0
        return (self.images_uploaded / self.total_images) * 100
    
    def is_complete(self) -> bool:
        """Check if session is complete."""
        return self.status in ['SYNCED', 'FAILED', 'PARTIAL']


class ImageUploadItem(models.Model):
    """
    Individual image item within an upload session.
    
    Links OfflineImageMetadata to ImageUploadSession for better tracking.
    """
    
    session = models.ForeignKey(
        ImageUploadSession,
        on_delete=models.CASCADE,
        related_name='upload_items',
        help_text="Upload session this item belongs to"
    )
    
    metadata = models.OneToOneField(
        'radiology.OfflineImageMetadata',
        on_delete=models.CASCADE,
        related_name='upload_item',
        help_text="Offline image metadata for this item"
    )
    
    # Position in session
    sequence_number = models.PositiveIntegerField(
        help_text="Sequence number of this image in the session"
    )
    
    # Status tracking
    upload_status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('METADATA_UPLOADED', 'Metadata Uploaded'),
            ('BINARY_UPLOADED', 'Binary Uploaded'),
            ('ACK_RECEIVED', 'ACK Received'),
            ('FAILED', 'Failed'),
        ],
        default='PENDING',
        help_text="Upload status of this specific image"
    )
    
    # Error tracking
    error_message = models.TextField(
        blank=True,
        help_text="Error message if upload failed"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    
    updated_at = models.DateTimeField(
        auto_now=True
    )
    
    class Meta:
        db_table = 'image_upload_items'
        ordering = ['session', 'sequence_number']
        indexes = [
            models.Index(fields=['session', 'sequence_number']),
            models.Index(fields=['upload_status']),
        ]
        unique_together = [['session', 'sequence_number']]
        verbose_name = 'Image Upload Item'
        verbose_name_plural = 'Image Upload Items'
    
    def __str__(self):
        return f"Upload Item {self.sequence_number} - {self.get_upload_status_display()}"
    
    def update_status(self, new_status: str, error_message: str = ''):
        """Update upload status and sync with session."""
        old_status = self.upload_status
        self.upload_status = new_status
        self.error_message = error_message
        self.save(update_fields=['upload_status', 'error_message', 'updated_at'])
        
        # Update session progress
        if new_status == 'ACK_RECEIVED' and old_status != 'ACK_RECEIVED':
            self.session.mark_image_uploaded()
        elif new_status == 'FAILED' and old_status != 'FAILED':
            self.session.mark_image_failed()


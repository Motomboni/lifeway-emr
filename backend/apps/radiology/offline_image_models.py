"""
Offline Image Upload Models - PACS-lite Implementation

Per EMR Context Document v2 (LOCKED):
- Images are stored locally first
- Metadata syncs before binaries
- No image is deleted locally until server ACK

Architecture (Non-Negotiable):
1. RadiologyOrder (online)
2. Perform imaging (offline)
3. Store locally: image_uuid, radiology_order_id, checksum
4. Queue metadata
5. Background sync
6. Server ACK
7. Upload binaries

Sync Rules:
- Images are immutable
- No overwrite allowed
- Checksums validated server-side
- Local copy deleted ONLY after ACK
"""
import uuid
import hashlib
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class OfflineImageMetadata(models.Model):
    """
    Queued metadata for offline images waiting to be synced.
    
    This model stores metadata that will be uploaded FIRST (before binaries).
    This ensures we have a record of the image even if the upload fails.
    
    Per EMR Context Document v2: "Metadata syncs before binaries"
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending - Metadata not yet uploaded'),
        ('METADATA_UPLOADED', 'Metadata Uploaded - Waiting for binary upload'),
        ('BINARY_UPLOADED', 'Binary Uploaded - Waiting for server ACK'),
        ('ACK_RECEIVED', 'ACK Received - Safe to delete local copy'),
        ('FAILED', 'Failed - Requires manual intervention'),
    ]
    
    # Unique identifier for the image (generated client-side)
    image_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
        help_text="Unique identifier for the image (generated client-side, UUID-based)"
    )
    
    # Link to radiology order
    radiology_order = models.ForeignKey(
        'radiology.RadiologyOrder',
        on_delete=models.CASCADE,
        related_name='offline_image_metadata',
        help_text="Radiology order this image belongs to"
    )
    
    # Metadata (uploaded FIRST)
    filename = models.CharField(
        max_length=255,
        help_text="Original filename of the image"
    )
    
    file_size = models.BigIntegerField(
        help_text="File size in bytes"
    )
    
    mime_type = models.CharField(
        max_length=100,
        help_text="MIME type of the image (e.g., 'image/jpeg', 'application/dicom')"
    )
    
    checksum = models.CharField(
        max_length=64,
        db_index=True,
        help_text="SHA-256 checksum of the image file (validated server-side)"
    )
    
    # Image metadata (DICOM tags or JPEG metadata)
    image_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Image metadata (DICOM tags, JPEG EXIF, etc.) - no raw binary"
    )
    
    # Upload tracking
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='PENDING',
        db_index=True,
        help_text="Current sync status of this image"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When metadata was queued (client-side timestamp)"
    )
    
    metadata_uploaded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When metadata was successfully uploaded to server"
    )
    
    binary_uploaded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When binary was successfully uploaded to server"
    )
    
    ack_received_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When server ACK was received (safe to delete local copy)"
    )
    
    failed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When upload failed (if status is FAILED)"
    )
    
    failure_reason = models.TextField(
        blank=True,
        help_text="Reason for failure (if status is FAILED)"
    )
    
    # Retry tracking
    retry_count = models.IntegerField(
        default=0,
        help_text="Number of times upload has been retried"
    )
    
    last_retry_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When upload was last retried"
    )
    
    class Meta:
        db_table = 'radiology_offline_image_metadata'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['radiology_order']),
            models.Index(fields=['image_uuid']),
            models.Index(fields=['checksum']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'Offline Image Metadata'
        verbose_name_plural = 'Offline Image Metadata'
    
    def __str__(self):
        return f"OfflineImageMetadata {self.image_uuid} - {self.filename} ({self.status})"
    
    def clean(self):
        """Validate offline image metadata."""
        errors = {}
        
        # Validate checksum format (SHA-256 is 64 hex characters)
        if self.checksum and len(self.checksum) != 64:
            errors['checksum'] = (
                "Checksum must be SHA-256 (64 hex characters). "
                f"Got {len(self.checksum)} characters."
            )
        
        # Validate file size
        if self.file_size and self.file_size <= 0:
            errors['file_size'] = "File size must be greater than zero."
        
        # Validate status transitions
        if self.pk:
            try:
                old_instance = OfflineImageMetadata.objects.get(pk=self.pk)
                # Only allow forward progress or retry from FAILED
                valid_transitions = {
                    'PENDING': ['METADATA_UPLOADED', 'FAILED'],
                    'METADATA_UPLOADED': ['BINARY_UPLOADED', 'FAILED'],
                    'BINARY_UPLOADED': ['ACK_RECEIVED', 'FAILED'],
                    'ACK_RECEIVED': [],  # Terminal state
                    'FAILED': ['PENDING'],  # Can retry
                }
                
                if old_instance.status != self.status:
                    if self.status not in valid_transitions.get(old_instance.status, []):
                        errors['status'] = (
                            f"Cannot transition from {old_instance.status} to {self.status}. "
                            f"Valid transitions: {valid_transitions.get(old_instance.status, [])}"
                        )
            except OfflineImageMetadata.DoesNotExist:
                pass
        
        if errors:
            raise ValidationError(errors)
    
    def mark_metadata_uploaded(self):
        """Mark metadata as successfully uploaded."""
        if self.status != 'PENDING':
            raise ValidationError(
                f"Cannot mark metadata as uploaded. Current status: {self.status}"
            )
        
        self.status = 'METADATA_UPLOADED'
        self.metadata_uploaded_at = timezone.now()
        self.save(update_fields=['status', 'metadata_uploaded_at'])
    
    def mark_binary_uploaded(self):
        """Mark binary as successfully uploaded."""
        if self.status != 'METADATA_UPLOADED':
            raise ValidationError(
                f"Cannot mark binary as uploaded. Current status: {self.status}. "
                "Metadata must be uploaded first."
            )
        
        self.status = 'BINARY_UPLOADED'
        self.binary_uploaded_at = timezone.now()
        self.save(update_fields=['status', 'binary_uploaded_at'])
    
    def mark_ack_received(self):
        """Mark server ACK as received (safe to delete local copy)."""
        if self.status != 'BINARY_UPLOADED':
            raise ValidationError(
                f"Cannot mark ACK as received. Current status: {self.status}. "
                "Binary must be uploaded first."
            )
        
        self.status = 'ACK_RECEIVED'
        self.ack_received_at = timezone.now()
        self.save(update_fields=['status', 'ack_received_at'])
    
    def mark_failed(self, reason: str):
        """Mark upload as failed."""
        self.status = 'FAILED'
        self.failed_at = timezone.now()
        self.failure_reason = reason
        self.retry_count += 1
        self.last_retry_at = timezone.now()
        self.save(update_fields=['status', 'failed_at', 'failure_reason', 'retry_count', 'last_retry_at'])


# Note: RadiologyImage model has been moved to pacs_lite_models.py
# This allows proper PACS-lite integration with Study/Series grouping


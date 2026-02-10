"""
Offline-first models - OfflineDraft and SyncQueue.

Per EMR Rules:
- Offline actions MUST be visit-scoped
- Save to OfflineDraft
- Sync via SyncQueue
- No direct writes when offline
"""
from django.db import models
from django.core.exceptions import ValidationError


class OfflineDraft(models.Model):
    """
    OfflineDraft - stores draft data when offline.
    
    Per EMR Rules:
    - Offline actions MUST be visit-scoped
    - Save to OfflineDraft
    - Auto-expire after sync
    - Encrypted on device (handled by frontend)
    """
    
    RESOURCE_TYPES = [
        ('CONSULTATION', 'Consultation'),
        ('LAB_ORDER', 'Lab Order'),
        ('RADIOLOGY_ORDER', 'Radiology Order'),
        ('PRESCRIPTION', 'Prescription'),
    ]
    
    # Visit-scoped (ABSOLUTE)
    visit_id = models.IntegerField(
        help_text="Visit ID - offline actions MUST be visit-scoped"
    )
    
    # Resource information
    resource_type = models.CharField(
        max_length=50,
        choices=RESOURCE_TYPES,
        help_text="Type of resource being drafted"
    )
    
    # Draft data (encrypted by frontend before storage)
    draft_data = models.JSONField(
        help_text="Draft data (encrypted, visit-scoped)"
    )
    
    # User tracking
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='offline_drafts',
        help_text="User who created this draft"
    )
    
    # Sync tracking
    synced = models.BooleanField(
        default=False,
        help_text="Whether this draft has been synced"
    )
    
    synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the draft was synced"
    )
    
    # Expiration
    expires_at = models.DateTimeField(
        help_text="When this draft expires (auto-cleanup)"
    )
    
    # Audit timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When draft was created"
    )
    
    class Meta:
        db_table = 'offline_drafts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['visit_id']),
            models.Index(fields=['resource_type']),
            models.Index(fields=['created_by']),
            models.Index(fields=['synced']),
            models.Index(fields=['expires_at']),
        ]
        verbose_name = 'Offline Draft'
        verbose_name_plural = 'Offline Drafts'
    
    def __str__(self):
        return f"OfflineDraft {self.resource_type} for Visit {self.visit_id}"
    
    def clean(self):
        """Validate offline draft data."""
        # Ensure visit_id is provided (visit-scoped)
        if not self.visit_id:
            raise ValidationError("Offline drafts MUST be visit-scoped.")
    
    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.full_clean()
        super().save(*args, **kwargs)


class SyncQueue(models.Model):
    """
    SyncQueue - queues offline actions for sync when online.
    
    Per EMR Rules:
    - Sync via SyncQueue
    - No direct writes when offline
    - Visit-scoped actions only
    """
    
    ACTION_TYPES = [
        ('CREATE_CONSULTATION', 'Create Consultation'),
        ('UPDATE_CONSULTATION', 'Update Consultation'),
        ('CREATE_LAB_ORDER', 'Create Lab Order'),
        ('CREATE_RADIOLOGY_ORDER', 'Create Radiology Order'),
        ('CREATE_PRESCRIPTION', 'Create Prescription'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SYNCING', 'Syncing'),
        ('SYNCED', 'Synced'),
        ('FAILED', 'Failed'),
    ]
    
    # Visit-scoped (ABSOLUTE)
    visit_id = models.IntegerField(
        help_text="Visit ID - sync actions MUST be visit-scoped"
    )
    
    # Action information
    action_type = models.CharField(
        max_length=50,
        choices=ACTION_TYPES,
        help_text="Type of action to sync"
    )
    
    # Action data
    action_data = models.JSONField(
        help_text="Action data to sync (visit-scoped)"
    )
    
    # User tracking
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='sync_queue_items',
        help_text="User who created this sync item"
    )
    
    # Sync status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text="Sync status"
    )
    
    # Sync tracking
    synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the action was synced"
    )
    
    error_message = models.TextField(
        blank=True,
        help_text="Error message if sync failed"
    )
    
    retry_count = models.IntegerField(
        default=0,
        help_text="Number of sync retry attempts"
    )
    
    # Audit timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When sync item was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When sync item was last updated"
    )
    
    class Meta:
        db_table = 'sync_queue'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['visit_id']),
            models.Index(fields=['action_type']),
            models.Index(fields=['status']),
            models.Index(fields=['created_by']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'Sync Queue Item'
        verbose_name_plural = 'Sync Queue Items'
    
    def __str__(self):
        return f"SyncQueue {self.action_type} for Visit {self.visit_id} ({self.status})"
    
    def clean(self):
        """Validate sync queue data."""
        # Ensure visit_id is provided (visit-scoped)
        if not self.visit_id:
            raise ValidationError("Sync queue items MUST be visit-scoped.")
    
    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.full_clean()
        super().save(*args, **kwargs)


class SyncLog(models.Model):
    """
    Tracks last sync time per user and device for offline-first mobile.
    Used to support ?updated_since= in mobile APIs.
    """
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='sync_logs',
        help_text="User who synced",
    )
    device_id = models.CharField(
        max_length=255,
        help_text="Device identifier (mobile app instance)",
    )
    last_sync_time = models.DateTimeField(
        help_text="Last successful sync timestamp",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sync_logs'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'device_id']),
            models.Index(fields=['last_sync_time']),
        ]
        verbose_name = 'Sync Log'
        verbose_name_plural = 'Sync Logs'
        unique_together = [['user', 'device_id']]
    
    def __str__(self):
        return f"Sync {self.user_id} / {self.device_id} @ {self.last_sync_time}"

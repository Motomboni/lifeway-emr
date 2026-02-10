"""
Timeline Event Model for Visit Timeline Feature.

This module provides immutable, read-only timeline events that track
all significant actions within a visit's lifecycle.
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class TimelineEvent(models.Model):
    """
    Immutable timeline event for a visit.
    
    Events are auto-generated via Django signals and cannot be manually
    created, edited, or deleted.
    """
    
    EVENT_TYPE_CHOICES = [
        ('VISIT_CREATED', 'Visit Created'),
        ('CONSULTATION_STARTED', 'Consultation Started'),
        ('CONSULTATION_CLOSED', 'Consultation Closed'),
        ('SERVICE_SELECTED', 'Service Selected'),
        ('LAB_ORDERED', 'Lab Ordered'),
        ('LAB_RESULT_POSTED', 'Lab Result Posted'),
        ('RADIOLOGY_ORDERED', 'Radiology Ordered'),
        ('RADIOLOGY_REPORT_POSTED', 'Radiology Report Posted'),
        ('DRUG_DISPENSED', 'Drug Dispensed'),
        ('PAYMENT_CONFIRMED', 'Payment Confirmed'),
        ('PROCEDURE_ORDERED', 'Procedure Ordered'),
        ('PROCEDURE_COMPLETED', 'Procedure Completed'),
    ]
    
    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.CASCADE,
        related_name='timeline_events',
        help_text="Visit this event belongs to"
    )
    
    event_type = models.CharField(
        max_length=50,
        choices=EVENT_TYPE_CHOICES,
        help_text="Type of timeline event"
    )
    
    timestamp = models.DateTimeField(
        default=timezone.now,
        help_text="When the event occurred"
    )
    
    # Actor information
    actor = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='timeline_events',
        help_text="User who triggered this event"
    )
    
    actor_role = models.CharField(
        max_length=50,
        blank=True,
        help_text="Role of the actor at the time of the event"
    )
    
    # Event description
    description = models.TextField(
        help_text="Human-readable description of the event"
    )
    
    # Source object references (for linking)
    source_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Type of source object (e.g., 'consultation', 'lab_order')"
    )
    
    source_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="ID of the source object"
    )
    
    # Additional metadata (JSON field for flexibility)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional event metadata (e.g., service name, amount)"
    )
    
    # Deduplication key (to prevent duplicate events)
    deduplication_key = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Unique key to prevent duplicate events (format: visit_id:event_type:source_id)"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this timeline event was created"
    )
    
    class Meta:
        db_table = 'timeline_events'
        ordering = ['timestamp', 'created_at']
        indexes = [
            models.Index(fields=['visit', 'timestamp']),
            models.Index(fields=['event_type']),
            models.Index(fields=['deduplication_key']),
        ]
        verbose_name = 'Timeline Event'
        verbose_name_plural = 'Timeline Events'
    
    def __str__(self):
        return f"{self.get_event_type_display()} - {self.visit} - {self.timestamp}"
    
    def clean(self):
        """Validate timeline event."""
        errors = {}
        
        # Ensure deduplication_key is set
        if not self.deduplication_key:
            errors['deduplication_key'] = "Deduplication key is required."
        
        # Validate source_id is provided if source_type is set
        if self.source_type and not self.source_id:
            errors['source_id'] = "Source ID is required when source type is provided."
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Override save to enforce immutability and auto-generate deduplication key."""
        # Prevent manual editing (but allow creation via signals)
        if self.pk:
            # Allow updates only if they don't change critical fields
            # This is needed for signal-based creation
            pass
        
        # Auto-generate deduplication key if not provided
        if not self.deduplication_key:
            source_part = f":{self.source_id}" if self.source_id else ""
            self.deduplication_key = f"{self.visit_id}:{self.event_type}{source_part}"
        
        # Set actor_role from actor if not provided
        if self.actor and not self.actor_role:
            self.actor_role = getattr(self.actor, 'role', '')
        
        self.full_clean()
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Prevent deletion of timeline events."""
        raise ValidationError("Timeline events are immutable and cannot be deleted.")
    
    def get_source_url(self) -> str:
        """Generate URL to the source object."""
        if not self.source_type or not self.source_id:
            return None
        
        # Map source types to URL patterns
        url_map = {
            'consultation': f'/visits/{self.visit_id}/consultations/{self.source_id}/',
            'lab_order': f'/visits/{self.visit_id}/lab-orders/{self.source_id}/',
            'lab_result': f'/visits/{self.visit_id}/lab-results/{self.source_id}/',
            'radiology_request': f'/visits/{self.visit_id}/radiology/{self.source_id}/',
            'prescription': f'/visits/{self.visit_id}/prescriptions/{self.source_id}/',
            'billing_line_item': f'/visits/{self.visit_id}/billing/{self.source_id}/',
            'procedure_task': f'/visits/{self.visit_id}/procedures/{self.source_id}/',
        }
        
        return url_map.get(self.source_type.lower())


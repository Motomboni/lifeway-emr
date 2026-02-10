"""
Revenue Leak Detection models.

Per EMR Rules:
- A revenue leak occurs when a clinical action is completed without a corresponding paid BillingLineItem
- Leaks must be detected idempotently
- Emergency overrides are excluded
- Leaks must be reviewed and resolved manually (no auto-fix)
"""
from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal


class LeakRecord(models.Model):
    """
    LeakRecord model - tracks revenue leaks detected in the system.
    
    A revenue leak occurs when a clinical action is completed without
    a corresponding paid BillingLineItem.
    
    Design Principles:
    1. Idempotent detection (same leak detected multiple times = same record)
    2. Manual resolution only (no auto-fix)
    3. Exclude emergency overrides
    4. Track estimated revenue loss
    """
    
    ENTITY_TYPE_CHOICES = [
        ('LAB_RESULT', 'Lab Result'),
        ('RADIOLOGY_REPORT', 'Radiology Report'),
        ('DRUG_DISPENSE', 'Drug Dispense'),
        ('PROCEDURE', 'Procedure'),
    ]
    
    # Entity identification
    entity_type = models.CharField(
        max_length=50,
        choices=ENTITY_TYPE_CHOICES,
        db_index=True,
        help_text="Type of entity that triggered the leak detection"
    )
    
    entity_id = models.PositiveIntegerField(
        db_index=True,
        help_text="ID of the entity that triggered the leak (LabResult.id, RadiologyRequest.id, etc.)"
    )
    
    # Service information
    service_code = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Service code from ServiceCatalog (if available)"
    )
    
    service_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Service name from ServiceCatalog (if available)"
    )
    
    # Financial impact
    estimated_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Estimated revenue loss (from ServiceCatalog.amount if available)"
    )
    
    # Visit context
    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.CASCADE,
        related_name='leak_records',
        help_text="Visit where the leak was detected"
    )
    
    # Detection tracking
    detected_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When the leak was first detected"
    )
    
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When the leak was resolved (manually)"
    )
    
    resolved_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leaks_resolved',
        help_text="User who resolved the leak"
    )
    
    resolution_notes = models.TextField(
        blank=True,
        help_text="Notes about how the leak was resolved"
    )
    
    # Additional context
    detection_context = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context about the detection (e.g., why no bill was found)"
    )
    
    class Meta:
        db_table = 'leak_records'
        ordering = ['-detected_at']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['visit']),
            models.Index(fields=['detected_at']),
            models.Index(fields=['resolved_at']),
            models.Index(fields=['service_code']),
            models.Index(fields=['entity_type', 'resolved_at']),
        ]
        # Unique constraint for idempotent detection
        constraints = [
            models.UniqueConstraint(
                fields=['entity_type', 'entity_id'],
                condition=models.Q(resolved_at__isnull=True),
                name='unique_unresolved_leak_per_entity'
            ),
        ]
        verbose_name = 'Revenue Leak Record'
        verbose_name_plural = 'Revenue Leak Records'
    
    def __str__(self):
        status = "Resolved" if self.resolved_at else "Unresolved"
        return f"{self.get_entity_type_display()} #{self.entity_id} - {self.estimated_amount} NGN ({status})"
    
    def clean(self):
        """Validate leak record data."""
        errors = {}
        
        # Validate estimated_amount
        if self.estimated_amount <= 0:
            errors['estimated_amount'] = "Estimated amount must be greater than zero."
        
        # Validate resolution
        if self.resolved_at and not self.resolved_by:
            errors['resolved_by'] = "Resolved leaks must have a resolver."
        
        if not self.resolved_at and self.resolved_by:
            errors['resolved_at'] = "Cannot set resolver without resolution timestamp."
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def resolve(self, user, notes: str = ''):
        """
        Manually resolve the leak.
        
        Args:
            user: User resolving the leak
            notes: Resolution notes
        """
        from django.utils import timezone
        
        if self.resolved_at:
            raise ValidationError("Leak is already resolved.")
        
        self.resolved_at = timezone.now()
        self.resolved_by = user
        self.resolution_notes = notes
        self.save()
    
    def is_resolved(self) -> bool:
        """Check if leak is resolved."""
        return self.resolved_at is not None


"""
Radiology Test Template models - pre-configured common radiology studies.

Templates help doctors quickly order common radiology studies
(e.g., "Chest X-Ray", "CT Head", "Abdominal Ultrasound")
"""
from django.db import models
from django.core.exceptions import ValidationError


class RadiologyTestTemplate(models.Model):
    """
    Template for common radiology studies.
    
    Examples:
    - Chest X-Ray
    - CT Scan Head
    - Abdominal Ultrasound
    - Pelvic Ultrasound
    - Lumbar Spine X-Ray
    """
    
    name = models.CharField(
        max_length=200,
        help_text="Template name (e.g., 'Chest X-Ray', 'CT Scan Head')"
    )
    
    category = models.CharField(
        max_length=100,
        blank=True,
        help_text="Template category (e.g., 'X-Ray', 'CT Scan', 'Ultrasound', 'MRI')"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Description of when to use this template"
    )
    
    # Template content - matches RadiologyRequest fields
    imaging_type = models.CharField(
        max_length=10,
        choices=[
            ('XRAY', 'X-Ray'),
            ('CT', 'CT Scan'),
            ('MRI', 'MRI'),
            ('US', 'Ultrasound'),
        ],
        help_text="Type of imaging study"
    )
    
    body_part = models.CharField(
        max_length=100,
        help_text="Body part to be imaged (e.g., 'Chest', 'Head', 'Abdomen')"
    )
    
    study_code = models.CharField(
        max_length=100,
        blank=True,
        help_text="Radiology study code/identifier"
    )
    
    default_clinical_indication = models.TextField(
        blank=True,
        help_text="Default clinical indication text (can be edited when applying template)"
    )
    
    default_priority = models.CharField(
        max_length=10,
        choices=[
            ('ROUTINE', 'Routine'),
            ('URGENT', 'Urgent'),
        ],
        default='ROUTINE',
        help_text="Default priority level"
    )
    
    # Metadata
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='radiology_test_templates_created',
        help_text="User who created this template"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this template is active and available for use"
    )
    
    usage_count = models.IntegerField(
        default=0,
        help_text="Number of times this template has been used"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'radiology_test_templates'
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['imaging_type']),
            models.Index(fields=['created_by']),
        ]
        verbose_name = 'Radiology Test Template'
        verbose_name_plural = 'Radiology Test Templates'
    
    def __str__(self):
        return f"{self.name} ({self.category or 'Uncategorized'})"
    
    def increment_usage(self):
        """Increment usage count."""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])


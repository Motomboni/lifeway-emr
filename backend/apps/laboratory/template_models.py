"""
Lab Test Template models - pre-configured common lab test combinations.

Templates help doctors quickly order common lab test panels
(e.g., "Complete Blood Count", "Liver Function Tests", "Basic Metabolic Panel")
"""
from django.db import models
from django.core.exceptions import ValidationError


class LabTestTemplate(models.Model):
    """
    Template for common lab test combinations.
    
    Examples:
    - Complete Blood Count (CBC)
    - Liver Function Tests (LFT)
    - Basic Metabolic Panel (BMP)
    - Lipid Profile
    - Thyroid Function Tests
    """
    
    name = models.CharField(
        max_length=200,
        help_text="Template name (e.g., 'Complete Blood Count', 'Liver Function Tests')"
    )
    
    category = models.CharField(
        max_length=100,
        blank=True,
        help_text="Template category (e.g., 'Hematology', 'Chemistry', 'Microbiology')"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Description of when to use this template"
    )
    
    # Template content
    tests = models.JSONField(
        help_text="List of test codes/names (JSON array, e.g., ['CBC', 'Hemoglobin', 'WBC Count'])"
    )
    
    default_clinical_indication = models.TextField(
        blank=True,
        help_text="Default clinical indication text (can be edited when applying template)"
    )
    
    # Metadata
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='lab_test_templates_created',
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
        db_table = 'lab_test_templates'
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['created_by']),
        ]
        verbose_name = 'Lab Test Template'
        verbose_name_plural = 'Lab Test Templates'
    
    def __str__(self):
        return f"{self.name} ({self.category or 'Uncategorized'})"
    
    def clean(self):
        """Validate template data."""
        if not self.tests or not isinstance(self.tests, list):
            raise ValidationError("Tests must be a non-empty list")
        
        if len(self.tests) == 0:
            raise ValidationError("Template must include at least one test")
    
    def increment_usage(self):
        """Increment usage count."""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])


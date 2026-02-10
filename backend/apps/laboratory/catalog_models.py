"""
Lab Test Catalog models - Manage available lab tests and reference ranges.
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator


class LabTestCatalog(models.Model):
    """
    Lab Test Catalog model - Available lab tests with reference ranges.
    
    This model stores the catalog of available lab tests that can be ordered.
    Each test has a code, name, category, and reference ranges.
    """
    
    CATEGORY_CHOICES = [
        ('HEMATOLOGY', 'Hematology'),
        ('CHEMISTRY', 'Chemistry'),
        ('MICROBIOLOGY', 'Microbiology'),
        ('IMMUNOLOGY', 'Immunology'),
        ('SEROLOGY', 'Serology'),
        ('ENDOCRINOLOGY', 'Endocrinology'),
        ('TOXICOLOGY', 'Toxicology'),
        ('URINALYSIS', 'Urinalysis'),
        ('BLOOD_BANK', 'Blood Bank'),
        ('MOLECULAR', 'Molecular'),
        ('OTHER', 'Other'),
    ]
    
    test_code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique code for the lab test (e.g., CBC, HGB, GLU)"
    )
    
    test_name = models.CharField(
        max_length=200,
        help_text="Full name of the lab test"
    )
    
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        help_text="Category of the lab test"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Description of what the test measures"
    )
    
    # Reference ranges
    reference_range_min = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum normal value (for numeric tests)"
    )
    
    reference_range_max = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum normal value (for numeric tests)"
    )
    
    reference_range_text = models.TextField(
        blank=True,
        help_text="Textual reference range (e.g., 'Negative', 'Positive', 'Normal')"
    )
    
    unit = models.CharField(
        max_length=50,
        blank=True,
        help_text="Unit of measurement (e.g., g/dL, mg/dL, cells/μL)"
    )
    
    # Test metadata
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this test is currently available for ordering"
    )
    
    requires_fasting = models.BooleanField(
        default=False,
        help_text="Whether patient must fast before this test"
    )
    
    turnaround_time_hours = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Expected turnaround time in hours"
    )
    
    specimen_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Type of specimen required (e.g., 'Blood', 'Urine', 'Stool')"
    )
    
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='lab_tests_created',
        help_text="User who created this test in the catalog"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the test was added to the catalog"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the test was last updated"
    )
    
    class Meta:
        db_table = 'lab_test_catalog'
        ordering = ['category', 'test_name']
        indexes = [
            models.Index(fields=['test_code']),
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
            models.Index(fields=['test_name']),
        ]
        verbose_name = 'Lab Test Catalog'
        verbose_name_plural = 'Lab Test Catalog'
    
    def __str__(self):
        return f"{self.test_code} - {self.test_name}"
    
    def clean(self):
        """Validate lab test catalog data."""
        # Ensure at least one reference range is provided
        if not self.reference_range_text:
            if self.reference_range_min is None and self.reference_range_max is None:
                raise ValidationError(
                    "Either reference_range_text or reference_range_min/max must be provided."
                )
        
        # Ensure min < max if both are provided
        if self.reference_range_min is not None and self.reference_range_max is not None:
            if self.reference_range_min >= self.reference_range_max:
                raise ValidationError(
                    "reference_range_min must be less than reference_range_max."
                )
    
    def save(self, *args, **kwargs):
        """Override save to run clean() validation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_reference_range_display(self):
        """Get formatted reference range string."""
        if self.reference_range_text:
            return self.reference_range_text
        
        if self.reference_range_min is not None and self.reference_range_max is not None:
            unit_str = f" {self.unit}" if self.unit else ""
            return f"{self.reference_range_min}{unit_str} - {self.reference_range_max}{unit_str}"
        
        if self.reference_range_min is not None:
            unit_str = f" {self.unit}" if self.unit else ""
            return f">= {self.reference_range_min}{unit_str}"
        
        if self.reference_range_max is not None:
            unit_str = f" {self.unit}" if self.unit else ""
            return f"<= {self.reference_range_max}{unit_str}"
        
        return "Not specified"

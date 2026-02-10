"""
Radiology Study Types Catalog models - Manage available radiology study types and protocols.
"""
from django.db import models
from django.core.exceptions import ValidationError


class RadiologyStudyType(models.Model):
    """
    Radiology Study Type Catalog model - Available radiology study types.
    
    This model stores the catalog of available radiology study types that can be ordered.
    Each study type has a code, name, category, and protocol information.
    """
    
    CATEGORY_CHOICES = [
        ('X_RAY', 'X-Ray'),
        ('CT_SCAN', 'CT Scan'),
        ('MRI', 'MRI'),
        ('ULTRASOUND', 'Ultrasound'),
        ('MAMMOGRAPHY', 'Mammography'),
        ('DEXA_SCAN', 'DEXA Scan'),
        ('NUCLEAR_MEDICINE', 'Nuclear Medicine'),
        ('FLUOROSCOPY', 'Fluoroscopy'),
        ('ANGIOGRAPHY', 'Angiography'),
        ('ECHOCARDIOGRAM', 'Echocardiogram'),
        ('OTHER', 'Other'),
    ]
    
    study_code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique code for the radiology study (e.g., CXR, CT-HEAD, MRI-BRAIN)"
    )
    
    study_name = models.CharField(
        max_length=200,
        help_text="Full name of the radiology study"
    )
    
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        help_text="Category of the radiology study"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Description of what the study examines"
    )
    
    protocol = models.TextField(
        blank=True,
        help_text="Protocol or procedure details for performing the study"
    )
    
    preparation_instructions = models.TextField(
        blank=True,
        help_text="Patient preparation instructions (e.g., fasting, contrast)"
    )
    
    contrast_required = models.BooleanField(
        default=False,
        help_text="Whether contrast agent is required"
    )
    
    contrast_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Type of contrast if required (e.g., IV, Oral, Rectal)"
    )
    
    estimated_duration_minutes = models.IntegerField(
        null=True,
        blank=True,
        help_text="Estimated duration of the study in minutes"
    )
    
    body_part = models.CharField(
        max_length=200,
        blank=True,
        help_text="Body part or region examined (e.g., Head, Chest, Abdomen)"
    )
    
    # Study metadata
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this study type is currently available for ordering"
    )
    
    requires_sedation = models.BooleanField(
        default=False,
        help_text="Whether sedation is required for this study"
    )
    
    radiation_dose = models.CharField(
        max_length=100,
        blank=True,
        help_text="Typical radiation dose (for studies involving radiation)"
    )
    
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='radiology_study_types_created',
        help_text="User who created this study type in the catalog"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the study type was added to the catalog"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the study type was last updated"
    )
    
    class Meta:
        db_table = 'radiology_study_types'
        ordering = ['category', 'study_name']
        indexes = [
            models.Index(fields=['study_code']),
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
            models.Index(fields=['study_name']),
        ]
        verbose_name = 'Radiology Study Type'
        verbose_name_plural = 'Radiology Study Types'
    
    def __str__(self):
        return f"{self.study_code} - {self.study_name}"
    
    def clean(self):
        """Validate radiology study type data."""
        # Ensure contrast type is provided if contrast is required
        if self.contrast_required and not self.contrast_type:
            raise ValidationError(
                "Contrast type must be specified when contrast is required."
            )
    
    def save(self, *args, **kwargs):
        """Override save to run clean() validation."""
        self.full_clean()
        super().save(*args, **kwargs)

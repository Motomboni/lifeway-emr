"""
Diagnosis Code models - ICD-11 code storage for consultations.

Per EMR Rules:
- Diagnosis codes are visit-scoped (via consultation)
- Multiple codes per consultation (primary + secondary)
- Codes can be manually entered or AI-generated
- Codes are used for billing, reporting, and analytics
"""
from django.db import models
from django.core.exceptions import ValidationError


class DiagnosisCode(models.Model):
    """
    Diagnosis code model - links ICD-11 codes to consultations.
    
    Supports multiple codes per consultation (primary + secondary).
    Codes can be manually entered or AI-generated.
    """
    
    CODE_TYPE_CHOICES = [
        ('ICD11', 'ICD-11'),
        ('ICD10', 'ICD-10'),  # For backward compatibility
    ]
    
    # Core relationship - visit-scoped via consultation
    consultation = models.ForeignKey(
        'consultations.Consultation',
        on_delete=models.CASCADE,
        related_name='diagnosis_codes',
        help_text="Consultation this code belongs to"
    )
    
    code_type = models.CharField(
        max_length=10,
        choices=CODE_TYPE_CHOICES,
        default='ICD11',
        help_text="Type of diagnosis code"
    )
    
    code = models.CharField(
        max_length=20,
        help_text="Diagnosis code (e.g., 'CA40.Z' for ICD-11)"
    )
    
    description = models.CharField(
        max_length=500,
        help_text="Description of the diagnosis code"
    )
    
    is_primary = models.BooleanField(
        default=False,
        help_text="True if this is the primary diagnosis"
    )
    
    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="AI confidence score (0-100) if code was AI-generated"
    )
    
    # Audit fields
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='diagnosis_codes_created',
        help_text="User who assigned this code"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When code was assigned"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When code was last updated"
    )
    
    class Meta:
        db_table = 'diagnosis_codes'
        ordering = ['-is_primary', 'created_at']
        indexes = [
            models.Index(fields=['consultation']),
            models.Index(fields=['code']),
            models.Index(fields=['is_primary']),
            models.Index(fields=['code_type']),
        ]
        verbose_name = 'Diagnosis Code'
        verbose_name_plural = 'Diagnosis Codes'
        # Ensure only one primary code per consultation
        constraints = [
            models.UniqueConstraint(
                fields=['consultation', 'is_primary'],
                condition=models.Q(is_primary=True),
                name='unique_primary_diagnosis'
            )
        ]
    
    def __str__(self):
        return f"{self.code} - {self.description[:50]}"
    
    def clean(self):
        """Validate diagnosis code."""
        # Validate code format (basic check)
        if self.code:
            self.code = self.code.strip().upper()
            if not self.code:
                raise ValidationError("Diagnosis code cannot be empty")
        
        # Validate description
        if not self.description or not self.description.strip():
            raise ValidationError("Diagnosis description is required")
        
        # If setting as primary, ensure no other primary exists
        if self.is_primary and self.consultation_id:
            existing_primary = DiagnosisCode.objects.filter(
                consultation=self.consultation,
                is_primary=True
            ).exclude(pk=self.pk if self.pk else None).first()
            
            if existing_primary:
                raise ValidationError(
                    f"Another primary diagnosis code already exists: {existing_primary.code}"
                )
    
    def save(self, *args, **kwargs):
        """Override save to ensure validation."""
        self.full_clean()
        
        # If setting as primary, unset other primary codes
        if self.is_primary and self.consultation_id:
            DiagnosisCode.objects.filter(
                consultation=self.consultation,
                is_primary=True
            ).exclude(pk=self.pk if self.pk else None).update(is_primary=False)
        
        super().save(*args, **kwargs)


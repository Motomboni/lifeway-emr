"""
Referral model - Patient referrals to specialists.
"""
from django.db import models
from django.core.exceptions import ValidationError


class Referral(models.Model):
    """
    Referral model - Refer patients to specialists.
    
    Per EMR Rules:
    - Visit-scoped: Must be associated with a visit
    - Consultation-dependent: Requires consultation
    - Doctor-only creation
    - Status tracking: PENDING, ACCEPTED, REJECTED, COMPLETED, CANCELLED
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    SPECIALTY_CHOICES = [
        ('CARDIOLOGY', 'Cardiology'),
        ('DERMATOLOGY', 'Dermatology'),
        ('ENDOCRINOLOGY', 'Endocrinology'),
        ('GASTROENTEROLOGY', 'Gastroenterology'),
        ('HEMATOLOGY', 'Hematology'),
        ('INFECTIOUS_DISEASE', 'Infectious Disease'),
        ('NEPHROLOGY', 'Nephrology'),
        ('NEUROLOGY', 'Neurology'),
        ('ONCOLOGY', 'Oncology'),
        ('OPHTHALMOLOGY', 'Ophthalmology'),
        ('ORTHOPEDICS', 'Orthopedics'),
        ('OTOLARYNGOLOGY', 'Otolaryngology'),
        ('PEDIATRICS', 'Pediatrics'),
        ('PSYCHIATRY', 'Psychiatry'),
        ('PULMONOLOGY', 'Pulmonology'),
        ('RHEUMATOLOGY', 'Rheumatology'),
        ('UROLOGY', 'Urology'),
        ('OTHER', 'Other'),
    ]
    
    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.CASCADE,
        related_name='referrals',
        help_text="Visit this referral belongs to"
    )
    
    consultation = models.ForeignKey(
        'consultations.Consultation',
        on_delete=models.PROTECT,
        related_name='referrals',
        help_text="Consultation that triggered this referral"
    )
    
    specialty = models.CharField(
        max_length=50,
        choices=SPECIALTY_CHOICES,
        help_text="Specialty to refer to"
    )
    
    specialist_name = models.CharField(
        max_length=200,
        help_text="Name of the specialist or clinic"
    )
    
    specialist_contact = models.CharField(
        max_length=200,
        blank=True,
        help_text="Contact information for the specialist"
    )
    
    reason = models.TextField(
        help_text="Reason for referral"
    )
    
    clinical_summary = models.TextField(
        blank=True,
        help_text="Clinical summary for the specialist"
    )
    
    urgency = models.CharField(
        max_length=20,
        choices=[
            ('ROUTINE', 'Routine'),
            ('URGENT', 'Urgent'),
            ('EMERGENCY', 'Emergency'),
        ],
        default='ROUTINE',
        help_text="Urgency level of the referral"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text="Current status of the referral"
    )
    
    referred_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='referrals_created',
        help_text="Doctor who created the referral"
    )
    
    accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the referral was accepted"
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the referral was completed"
    )
    
    specialist_notes = models.TextField(
        blank=True,
        help_text="Notes from the specialist"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the referral was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the referral was last updated"
    )
    
    class Meta:
        db_table = 'referrals'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['visit']),
            models.Index(fields=['consultation']),
            models.Index(fields=['status']),
            models.Index(fields=['specialty']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'Referral'
        verbose_name_plural = 'Referrals'
    
    def __str__(self):
        return f"Referral {self.id} - {self.specialty} ({self.status})"
    
    def clean(self):
        """Validate referral data."""
        # Ensure consultation belongs to visit
        if self.consultation and self.visit:
            if self.consultation.visit_id != self.visit_id:
                raise ValidationError(
                    "Consultation must belong to the same visit as the referral."
                )
        
        # Ensure visit is not CLOSED when creating/updating
        if self.visit and self.visit.status == 'CLOSED':
            if not self.pk:  # New referral
                raise ValidationError(
                    "Cannot create referral for a CLOSED visit."
                )
            else:  # Updating existing referral
                # Allow status updates only
                old_referral = Referral.objects.get(pk=self.pk)
                if self.status != old_referral.status:
                    # Status change is allowed even for closed visits
                    pass
                else:
                    raise ValidationError(
                        "Cannot modify referral details for a CLOSED visit. "
                        "Only status updates are allowed."
                    )
    
    def save(self, *args, **kwargs):
        """Override save to run clean() validation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def accept(self):
        """Mark referral as accepted."""
        from django.utils import timezone
        self.status = 'ACCEPTED'
        self.accepted_at = timezone.now()
        self.save(update_fields=['status', 'accepted_at'])
    
    def complete(self):
        """Mark referral as completed."""
        from django.utils import timezone
        self.status = 'COMPLETED'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])
    
    def cancel(self):
        """Cancel the referral."""
        self.status = 'CANCELLED'
        self.save(update_fields=['status'])

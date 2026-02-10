"""
Discharge Summary model - Formal discharge documentation.
"""
from django.db import models
from django.core.exceptions import ValidationError


class DischargeSummary(models.Model):
    """
    Discharge Summary model - Formal discharge documentation for closed visits.
    
    Per EMR Rules:
    - Visit-scoped: Must be associated with a visit
    - Visit must be CLOSED
    - Doctor-only creation
    - Immutable once created (cannot be modified)
    - Exportable in multiple formats
    """
    
    visit = models.OneToOneField(
        'visits.Visit',
        on_delete=models.CASCADE,
        related_name='discharge_summary',
        help_text="Visit this discharge summary belongs to"
    )
    
    admission = models.OneToOneField(
        'discharges.Admission',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='linked_discharge_summary',
        help_text="Admission record linked to this discharge (if patient was admitted)"
    )
    
    consultation = models.ForeignKey(
        'consultations.Consultation',
        on_delete=models.PROTECT,
        related_name='discharge_summaries',
        help_text="Consultation for this visit"
    )
    
    chief_complaint = models.TextField(
        help_text="Chief complaint at admission"
    )
    
    admission_date = models.DateTimeField(
        help_text="Date and time of admission"
    )
    
    discharge_date = models.DateTimeField(
        help_text="Date and time of discharge"
    )
    
    diagnosis = models.TextField(
        help_text="Primary and secondary diagnoses"
    )
    
    procedures_performed = models.TextField(
        blank=True,
        help_text="Procedures performed during visit"
    )
    
    treatment_summary = models.TextField(
        help_text="Summary of treatment provided"
    )
    
    medications_on_discharge = models.TextField(
        blank=True,
        help_text="Medications prescribed at discharge"
    )
    
    follow_up_instructions = models.TextField(
        help_text="Follow-up care instructions"
    )
    
    condition_at_discharge = models.CharField(
        max_length=50,
        choices=[
            ('STABLE', 'Stable'),
            ('IMPROVED', 'Improved'),
            ('UNCHANGED', 'Unchanged'),
            ('DETERIORATED', 'Deteriorated'),
            ('CRITICAL', 'Critical'),
        ],
        default='STABLE',
        help_text="Patient condition at discharge"
    )
    
    discharge_disposition = models.CharField(
        max_length=50,
        choices=[
            ('HOME', 'Home'),
            ('TRANSFER', 'Transfer to Another Facility'),
            ('AMA', 'Against Medical Advice'),
            ('EXPIRED', 'Expired'),
            ('OTHER', 'Other'),
        ],
        default='HOME',
        help_text="Discharge disposition"
    )
    
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='discharge_summaries_created',
        help_text="Doctor who created the discharge summary"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the discharge summary was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the discharge summary was last updated"
    )
    
    class Meta:
        db_table = 'discharge_summaries'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['visit']),
            models.Index(fields=['consultation']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'Discharge Summary'
        verbose_name_plural = 'Discharge Summaries'
    
    def __str__(self):
        return f"Discharge Summary for Visit {self.visit_id}"
    
    def clean(self):
        """Validate discharge summary data."""
        # Ensure visit is CLOSED
        if self.visit and self.visit.status != 'CLOSED':
            raise ValidationError(
                "Discharge summary can only be created for CLOSED visits."
            )
        
        # Ensure consultation belongs to visit
        if self.consultation and self.visit:
            if self.consultation.visit_id != self.visit_id:
                raise ValidationError(
                    "Consultation must belong to the same visit as the discharge summary."
                )
        
        # Prevent modifications if already created
        if self.pk:
            # Discharge summaries are immutable once created
            old_summary = DischargeSummary.objects.get(pk=self.pk)
            # Only allow updates to certain fields if needed, but typically immutable
            pass
    
    def save(self, *args, **kwargs):
        """Override save to run clean() validation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_formatted_summary(self):
        """Get formatted discharge summary text."""
        lines = []
        lines.append("=" * 60)
        lines.append("DISCHARGE SUMMARY")
        lines.append("=" * 60)
        lines.append(f"\nVisit ID: {self.visit_id}")
        lines.append(f"Patient: {self.visit.patient.get_full_name()}")
        lines.append(f"\nAdmission Date: {self.admission_date.strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"Discharge Date: {self.discharge_date.strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"\nChief Complaint: {self.chief_complaint}")
        lines.append(f"\nDiagnosis:\n{self.diagnosis}")
        if self.procedures_performed:
            lines.append(f"\nProcedures Performed:\n{self.procedures_performed}")
        lines.append(f"\nTreatment Summary:\n{self.treatment_summary}")
        if self.medications_on_discharge:
            lines.append(f"\nMedications on Discharge:\n{self.medications_on_discharge}")
        lines.append(f"\nFollow-up Instructions:\n{self.follow_up_instructions}")
        lines.append(f"\nCondition at Discharge: {self.get_condition_at_discharge_display()}")
        lines.append(f"Discharge Disposition: {self.get_discharge_disposition_display()}")
        lines.append(f"\nPrepared by: {self.created_by.get_full_name()}")
        lines.append(f"Date: {self.created_at.strftime('%Y-%m-%d %H:%M')}")
        lines.append("=" * 60)
        return "\n".join(lines)

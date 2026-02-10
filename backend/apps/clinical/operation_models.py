"""
Operation Notes models - surgical operation documentation.

Per EMR Rules:
- Operations are visit-scoped (ForeignKey to Visit)
- Operations require consultation context
- Operations are doctor/surgeon-only creation
- Operations are immutable after creation
- Operations include detailed surgical documentation
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class OperationNote(models.Model):
    """
    Operation Note model - surgical operation documentation.
    
    Per EMR Rules:
    - Visit-scoped: Must be associated with a visit
    - Consultation-dependent: Must have a consultation
    - Doctor-only creation (validated in clean())
    - Immutable after creation
    - Comprehensive surgical documentation
    """
    
    class OperationType(models.TextChoices):
        MAJOR_SURGERY = 'MAJOR_SURGERY', 'Major Surgery'
        MINOR_SURGERY = 'MINOR_SURGERY', 'Minor Surgery'
        ENDOSCOPIC = 'ENDOSCOPIC', 'Endoscopic Procedure'
        LAPAROSCOPIC = 'LAPAROSCOPIC', 'Laparoscopic Procedure'
        DIAGNOSTIC = 'DIAGNOSTIC', 'Diagnostic Procedure'
        THERAPEUTIC = 'THERAPEUTIC', 'Therapeutic Procedure'
        OTHER = 'OTHER', 'Other'
    
    class AnesthesiaType(models.TextChoices):
        GENERAL = 'GENERAL', 'General Anesthesia'
        REGIONAL = 'REGIONAL', 'Regional Anesthesia'
        LOCAL = 'LOCAL', 'Local Anesthesia'
        SEDATION = 'SEDATION', 'Conscious Sedation'
        NONE = 'NONE', 'No Anesthesia'
        OTHER = 'OTHER', 'Other'
    
    # Core relationships
    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.CASCADE,
        related_name='operation_notes',
        help_text="Visit this operation note belongs to. Visit-scoped per EMR rules."
    )
    
    consultation = models.ForeignKey(
        'consultations.Consultation',
        on_delete=models.PROTECT,
        related_name='operation_notes',
        help_text="Consultation this operation belongs to. Required for clinical context."
    )
    
    surgeon = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='operations_performed',
        help_text="Surgeon/Doctor who performed the operation. PROTECT prevents deletion."
    )
    
    assistant_surgeon = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operations_assisted',
        help_text="Assistant surgeon (if any)"
    )
    
    anesthetist = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operations_anesthetized',
        help_text="Anesthetist who administered anesthesia"
    )
    
    # Operation details
    operation_type = models.CharField(
        max_length=50,
        choices=OperationType.choices,
        default=OperationType.OTHER,
        help_text="Type of operation"
    )
    
    operation_name = models.CharField(
        max_length=255,
        help_text="Name of the operation/procedure"
    )
    
    preoperative_diagnosis = models.TextField(
        help_text="Preoperative diagnosis"
    )
    
    postoperative_diagnosis = models.TextField(
        blank=True,
        help_text="Postoperative diagnosis (if different)"
    )
    
    indication = models.TextField(
        help_text="Clinical indication for the operation"
    )
    
    # Anesthesia details
    anesthesia_type = models.CharField(
        max_length=50,
        choices=AnesthesiaType.choices,
        default=AnesthesiaType.GENERAL,
        help_text="Type of anesthesia used"
    )
    
    anesthesia_notes = models.TextField(
        blank=True,
        help_text="Additional anesthesia notes"
    )
    
    # Procedure details
    procedure_description = models.TextField(
        help_text="Detailed description of the procedure performed"
    )
    
    findings = models.TextField(
        blank=True,
        help_text="Intraoperative findings"
    )
    
    technique = models.TextField(
        blank=True,
        help_text="Surgical technique used"
    )
    
    complications = models.TextField(
        blank=True,
        help_text="Any complications encountered"
    )
    
    estimated_blood_loss = models.CharField(
        max_length=100,
        blank=True,
        help_text="Estimated blood loss (e.g., '200ml', 'Minimal')"
    )
    
    specimens_sent = models.TextField(
        blank=True,
        help_text="Specimens sent for pathology (if any)"
    )
    
    # Postoperative details
    postoperative_plan = models.TextField(
        blank=True,
        help_text="Postoperative care plan"
    )
    
    postoperative_instructions = models.TextField(
        blank=True,
        help_text="Postoperative instructions for patient"
    )
    
    # Timestamps
    operation_date = models.DateTimeField(
        help_text="Date and time of the operation"
    )
    
    operation_duration_minutes = models.IntegerField(
        null=True,
        blank=True,
        help_text="Duration of operation in minutes"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the operation note was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the operation note was last updated"
    )
    
    class Meta:
        db_table = 'operation_notes'
        ordering = ['-operation_date']
        indexes = [
            models.Index(fields=['visit', '-operation_date']),
            models.Index(fields=['consultation']),
            models.Index(fields=['surgeon']),
            models.Index(fields=['operation_type']),
        ]
        verbose_name = 'Operation Note'
        verbose_name_plural = 'Operation Notes'
    
    def __str__(self):
        return f"Operation Note {self.id}: {self.operation_name} for Visit {self.visit_id}"
    
    def clean(self):
        """Validate operation note data."""
        # Ensure visit is OPEN when creating note
        if self.visit_id and not self.pk:  # New note
            visit = self.visit
            if visit.status == 'CLOSED':
                raise ValidationError("Cannot create operation note for a CLOSED visit.")
        
        # Ensure consultation belongs to same visit
        if self.consultation_id and self.visit_id:
            if self.consultation.visit_id != self.visit_id:
                raise ValidationError("Consultation does not belong to this Visit.")
            
            # Consultation must be ACTIVE or CLOSED (not PENDING)
            if self.consultation.status == 'PENDING':
                raise ValidationError(
                    "Cannot create operation note for a PENDING consultation. "
                    "Consultation must be ACTIVE or CLOSED."
                )
        
        # Ensure surgeon is a Doctor
        if self.surgeon_id:
            user_role = getattr(self.surgeon, 'role', None)
            if not user_role:
                user_role = getattr(self.surgeon, 'get_role', lambda: None)()
            
            if user_role != 'DOCTOR':
                raise ValidationError("Only Doctors can create operation notes.")
        
        # Ensure assistant surgeon is a Doctor (if provided)
        if self.assistant_surgeon_id:
            user_role = getattr(self.assistant_surgeon, 'role', None)
            if not user_role:
                user_role = getattr(self.assistant_surgeon, 'get_role', lambda: None)()
            
            if user_role != 'DOCTOR':
                raise ValidationError("Assistant surgeon must be a Doctor.")
    
    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.full_clean()
        super().save(*args, **kwargs)

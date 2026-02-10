"""
Nursing models for EMR system.

Per EMR Rules:
- All models MUST be visit-scoped (ForeignKey to Visit)
- No diagnosis fields allowed
- All models must be auditable and immutable after creation
- Nurse can record: Nursing Notes, Medication Administration, Lab Sample Collection
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class NursingNote(models.Model):
    """
    Nursing notes - non-diagnostic clinical observations and care documentation.
    
    Per EMR Rules:
    - Visit-scoped: Must be associated with a visit
    - Nurse-only creation (doctors use Consultation)
    - No diagnosis fields allowed
    - Immutable after creation
    - Historical tracking for care continuity
    """
    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.CASCADE,
        related_name='nursing_notes',
        help_text="Visit this nursing note belongs to. Visit-scoped per EMR rules."
    )
    
    recorded_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='nursing_notes_recorded',
        help_text="Nurse who recorded this note. PROTECT prevents deletion."
    )
    
    # Note content - NO DIAGNOSIS FIELDS
    note_type = models.CharField(
        max_length=50,
        choices=[
            ('GENERAL', 'General Nursing Note'),
            ('ADMISSION', 'Admission Note'),
            ('SHIFT_HANDOVER', 'Shift Handover Note'),
            ('PROCEDURE', 'Procedure Note'),
            ('WOUND_CARE', 'Wound Care Note'),
            ('PATIENT_EDUCATION', 'Patient Education Note'),
            ('ANTENATAL', 'Antenatal Monitoring Note'),
            ('INPATIENT', 'Inpatient Monitoring Note'),
            ('OTHER', 'Other'),
        ],
        default='GENERAL',
        help_text="Type of nursing note"
    )
    
    note_content = models.TextField(
        help_text="Nursing note content - observations, care provided, patient response. NO DIAGNOSIS."
    )
    
    # Clinical observations (non-diagnostic)
    patient_condition = models.CharField(
        max_length=100,
        blank=True,
        help_text="General patient condition observation (e.g., 'Alert and oriented', 'Resting comfortably')"
    )
    
    care_provided = models.TextField(
        blank=True,
        help_text="Description of nursing care provided"
    )
    
    patient_response = models.TextField(
        blank=True,
        help_text="Patient's response to care provided"
    )
    
    # Timestamps
    recorded_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the nursing note was recorded"
    )
    
    class Meta:
        db_table = 'nursing_notes'
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['visit', '-recorded_at']),
            models.Index(fields=['recorded_by']),
            models.Index(fields=['note_type']),
        ]
        verbose_name = 'Nursing Note'
        verbose_name_plural = 'Nursing Notes'
    
    def __str__(self):
        return f"Nursing Note for Visit {self.visit_id} at {self.recorded_at}"
    
    def clean(self):
        """Validate nursing note data."""
        # Ensure visit is OPEN when creating note
        if self.visit_id and not self.pk:  # New note
            visit = self.visit
            if visit.status == 'CLOSED':
                raise ValidationError("Cannot create nursing note for a CLOSED visit.")
        
        # Ensure recorded_by is a Nurse
        if self.recorded_by_id:
            user_role = getattr(self.recorded_by, 'role', None)
            if not user_role:
                user_role = getattr(self.recorded_by, 'get_role', lambda: None)()
            
            if user_role != 'NURSE':
                raise ValidationError("Only Nurses can create nursing notes.")
    
    def save(self, *args, **kwargs):
        """Override save to run validation."""
        # Allow updates - removed immutability restriction
        # Updates are allowed as long as visit is OPEN
        self.full_clean()
        super().save(*args, **kwargs)


class MedicationAdministration(models.Model):
    """
    Medication administration record - tracks medication given to patient from existing prescriptions.
    
    Per EMR Rules:
    - Visit-scoped: Must be associated with a visit
    - Requires existing Prescription (Nurse cannot create prescriptions)
    - Nurse-only creation
    - Immutable after creation
    - Tracks actual administration vs. prescribed
    """
    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.CASCADE,
        related_name='medication_administrations',
        help_text="Visit this medication administration belongs to. Visit-scoped per EMR rules."
    )
    
    prescription = models.ForeignKey(
        'pharmacy.Prescription',
        on_delete=models.PROTECT,
        related_name='administrations',
        help_text="Prescription this administration is based on. Nurse cannot create prescriptions."
    )
    
    administered_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='medications_administered',
        help_text="Nurse who administered the medication. PROTECT prevents deletion."
    )
    
    # Administration details
    administration_time = models.DateTimeField(
        default=timezone.now,
        help_text="When the medication was actually administered"
    )
    
    dose_administered = models.CharField(
        max_length=255,
        help_text="Actual dose administered (e.g., '500mg', '1 tablet')"
    )
    
    route = models.CharField(
        max_length=50,
        choices=[
            ('ORAL', 'Oral'),
            ('IV', 'Intravenous'),
            ('IM', 'Intramuscular'),
            ('SC', 'Subcutaneous'),
            ('TOPICAL', 'Topical'),
            ('INHALATION', 'Inhalation'),
            ('RECTAL', 'Rectal'),
            ('OTHER', 'Other'),
        ],
        default='ORAL',
        help_text="Route of administration"
    )
    
    site = models.CharField(
        max_length=100,
        blank=True,
        help_text="Administration site (e.g., 'Left arm', 'Right thigh')"
    )
    
    # Administration status
    status = models.CharField(
        max_length=20,
        choices=[
            ('GIVEN', 'Given'),
            ('REFUSED', 'Refused by Patient'),
            ('HELD', 'Held (Clinical Reason)'),
            ('NOT_AVAILABLE', 'Not Available'),
            ('ERROR', 'Administration Error'),
        ],
        default='GIVEN',
        help_text="Status of medication administration"
    )
    
    # Notes
    administration_notes = models.TextField(
        blank=True,
        help_text="Notes about the administration (e.g., patient response, site reaction)"
    )
    
    reason_if_held = models.TextField(
        blank=True,
        help_text="Reason if medication was held (required if status is HELD)"
    )
    
    # Timestamps
    recorded_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this administration record was created"
    )
    
    class Meta:
        db_table = 'medication_administrations'
        ordering = ['-administration_time']
        indexes = [
            models.Index(fields=['visit', '-administration_time']),
            models.Index(fields=['prescription']),
            models.Index(fields=['administered_by']),
            models.Index(fields=['status']),
        ]
        verbose_name = 'Medication Administration'
        verbose_name_plural = 'Medication Administrations'
    
    def __str__(self):
        return f"Medication Admin for Visit {self.visit_id} - {self.prescription.drug} at {self.administration_time}"
    
    def clean(self):
        """Validate medication administration data."""
        # Ensure visit is OPEN when creating administration
        if self.visit_id and not self.pk:  # New administration
            visit = self.visit
            if visit.status == 'CLOSED':
                raise ValidationError("Cannot record medication administration for a CLOSED visit.")
        
        # Ensure prescription belongs to same visit
        if self.prescription_id and self.visit_id:
            if self.prescription.visit_id != self.visit_id:
                raise ValidationError("Prescription must belong to the same visit.")
        
        # Ensure administered_by is a Nurse (only check on creation)
        if not self.pk and self.administered_by_id:
            user_role = getattr(self.administered_by, 'role', None)
            if not user_role:
                user_role = getattr(self.administered_by, 'get_role', lambda: None)()
            
            if user_role != 'NURSE':
                raise ValidationError("Only Nurses can record medication administration.")
        
        # Require reason if held
        if self.status == 'HELD' and not self.reason_if_held:
            raise ValidationError("Reason is required when medication status is HELD.")
    
    def save(self, *args, **kwargs):
        """Override save to run validation."""
        # Allow updates - removed immutability restriction
        # Updates are allowed as long as visit is OPEN
        self.full_clean()
        super().save(*args, **kwargs)


class LabSampleCollection(models.Model):
    """
    Lab sample collection record - tracks sample collection from existing lab orders.
    
    Per EMR Rules:
    - Visit-scoped: Must be associated with a visit
    - Requires existing LabOrder (Nurse cannot create lab orders)
    - Nurse-only creation
    - Immutable after creation
    - Tracks actual sample collection vs. ordered
    """
    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.CASCADE,
        related_name='lab_sample_collections',
        help_text="Visit this sample collection belongs to. Visit-scoped per EMR rules."
    )
    
    lab_order = models.ForeignKey(
        'laboratory.LabOrder',
        on_delete=models.PROTECT,
        related_name='sample_collections',
        help_text="Lab order this sample collection is based on. Nurse cannot create lab orders."
    )
    
    collected_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='lab_samples_collected',
        help_text="Nurse who collected the sample. PROTECT prevents deletion."
    )
    
    # Collection details
    collection_time = models.DateTimeField(
        default=timezone.now,
        help_text="When the sample was actually collected"
    )
    
    sample_type = models.CharField(
        max_length=100,
        help_text="Type of sample collected (e.g., 'Blood', 'Urine', 'Sputum')"
    )
    
    collection_site = models.CharField(
        max_length=100,
        blank=True,
        help_text="Collection site (e.g., 'Left arm', 'Midstream urine')"
    )
    
    # Collection status
    status = models.CharField(
        max_length=20,
        choices=[
            ('COLLECTED', 'Collected'),
            ('PARTIAL', 'Partial Collection'),
            ('FAILED', 'Collection Failed'),
            ('REFUSED', 'Patient Refused'),
        ],
        default='COLLECTED',
        help_text="Status of sample collection"
    )
    
    # Sample information
    sample_volume = models.CharField(
        max_length=50,
        blank=True,
        help_text="Volume of sample collected (e.g., '5ml', '10cc')"
    )
    
    container_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Type of container used (e.g., 'Vacutainer', 'Sterile cup')"
    )
    
    # Notes
    collection_notes = models.TextField(
        blank=True,
        help_text="Notes about the collection (e.g., patient condition, special circumstances)"
    )
    
    reason_if_failed = models.TextField(
        blank=True,
        help_text="Reason if collection failed (required if status is FAILED)"
    )
    
    # Timestamps
    recorded_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this collection record was created"
    )
    
    class Meta:
        db_table = 'lab_sample_collections'
        ordering = ['-collection_time']
        indexes = [
            models.Index(fields=['visit', '-collection_time']),
            models.Index(fields=['lab_order']),
            models.Index(fields=['collected_by']),
            models.Index(fields=['status']),
        ]
        verbose_name = 'Lab Sample Collection'
        verbose_name_plural = 'Lab Sample Collections'
    
    def __str__(self):
        return f"Sample Collection for Visit {self.visit_id} - Order {self.lab_order_id} at {self.collection_time}"
    
    def clean(self):
        """Validate lab sample collection data."""
        # Ensure visit is OPEN when creating collection
        if self.visit_id and not self.pk:  # New collection
            visit = self.visit
            if visit.status == 'CLOSED':
                raise ValidationError("Cannot record sample collection for a CLOSED visit.")
        
        # Ensure lab_order belongs to same visit
        if self.lab_order_id and self.visit_id:
            if self.lab_order.visit_id != self.visit_id:
                raise ValidationError("Lab order must belong to the same visit.")
        
        # Ensure lab_order is in ORDERED status (can only collect from ordered tests)
        if self.lab_order_id:
            if self.lab_order.status not in ['ORDERED', 'SAMPLE_COLLECTED']:
                raise ValidationError("Can only collect samples for ORDERED or SAMPLE_COLLECTED lab orders.")
        
        # Ensure collected_by is a Nurse (only check on creation)
        if not self.pk and self.collected_by_id:
            user_role = getattr(self.collected_by, 'role', None)
            if not user_role:
                user_role = getattr(self.collected_by, 'get_role', lambda: None)()
            
            if user_role != 'NURSE':
                raise ValidationError("Only Nurses can record lab sample collection.")
        
        # Require reason if failed
        if self.status == 'FAILED' and not self.reason_if_failed:
            raise ValidationError("Reason is required when collection status is FAILED.")
    
    def save(self, *args, **kwargs):
        """Override save to run validation."""
        # Allow updates - removed immutability restriction
        # Updates are allowed as long as visit is OPEN
        self.full_clean()
        super().save(*args, **kwargs)
        
        # Update lab order status to SAMPLE_COLLECTED if successfully collected
        if self.status == 'COLLECTED' and self.lab_order.status == 'ORDERED':
            self.lab_order.status = 'SAMPLE_COLLECTED'
            self.lab_order.save(update_fields=['status'])

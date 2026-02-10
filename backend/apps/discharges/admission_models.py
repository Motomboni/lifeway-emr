"""
Admission models - Ward, Bed, and Admission tracking.

Per EMR Rules:
- Visit-scoped: Admissions are tied to visits
- Doctor-only admission creation
- Bed availability tracking
- Admission status separate from visit status
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class Ward(models.Model):
    """
    Ward model - Represents a hospital ward/unit.
    
    Examples: General Ward, ICU, Maternity, Pediatrics, etc.
    """
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Ward name (e.g., 'General Ward', 'ICU', 'Maternity')"
    )
    
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Ward code (e.g., 'GW', 'ICU', 'MAT')"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Description of the ward"
    )
    
    capacity = models.IntegerField(
        default=0,
        help_text="Total number of beds in this ward"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this ward is currently active"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'wards'
        ordering = ['name']
        verbose_name = 'Ward'
        verbose_name_plural = 'Wards'
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def get_available_beds_count(self):
        """Get count of available beds in this ward."""
        return self.beds.filter(is_available=True, is_active=True).count()
    
    def get_occupied_beds_count(self):
        """Get count of occupied beds in this ward."""
        return self.beds.filter(is_available=False, is_active=True).count()


class Bed(models.Model):
    """
    Bed model - Represents a bed within a ward.
    """
    ward = models.ForeignKey(
        Ward,
        on_delete=models.CASCADE,
        related_name='beds',
        help_text="Ward this bed belongs to"
    )
    
    bed_number = models.CharField(
        max_length=50,
        help_text="Bed number or identifier (e.g., 'A1', 'B5', 'ICU-1')"
    )
    
    bed_type = models.CharField(
        max_length=50,
        choices=[
            ('STANDARD', 'Standard'),
            ('PRIVATE', 'Private'),
            ('SEMI_PRIVATE', 'Semi-Private'),
            ('ICU', 'ICU'),
            ('ISOLATION', 'Isolation'),
            ('MATERNITY', 'Maternity'),
        ],
        default='STANDARD',
        help_text="Type of bed"
    )
    
    is_available = models.BooleanField(
        default=True,
        help_text="Whether this bed is currently available"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this bed is active (not decommissioned)"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this bed"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'beds'
        unique_together = [['ward', 'bed_number']]
        ordering = ['ward', 'bed_number']
        indexes = [
            models.Index(fields=['ward', 'is_available']),
        ]
        verbose_name = 'Bed'
        verbose_name_plural = 'Beds'
    
    def __str__(self):
        return f"{self.ward.name} - Bed {self.bed_number}"
    
    def clean(self):
        """Validate bed data."""
        if self.ward and not self.ward.is_active:
            raise ValidationError("Cannot assign bed to an inactive ward.")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Admission(models.Model):
    """
    Admission model - Tracks patient admission to a ward/bed.
    
    Per EMR Rules:
    - Visit-scoped: Must be associated with a visit
    - Doctor-only creation
    - Admission status separate from visit status
    - Links to discharge summary when patient is discharged
    """
    visit = models.OneToOneField(
        'visits.Visit',
        on_delete=models.CASCADE,
        related_name='admission',
        help_text="Visit this admission belongs to"
    )
    
    ward = models.ForeignKey(
        Ward,
        on_delete=models.PROTECT,
        related_name='admissions',
        help_text="Ward patient is admitted to"
    )
    
    bed = models.ForeignKey(
        Bed,
        on_delete=models.PROTECT,
        related_name='admissions',
        help_text="Bed patient is assigned to"
    )
    
    admission_type = models.CharField(
        max_length=50,
        choices=[
            ('EMERGENCY', 'Emergency'),
            ('ELECTIVE', 'Elective'),
            ('OBSERVATION', 'Observation'),
            ('DAY_CARE', 'Day Care'),
        ],
        default='ELECTIVE',
        help_text="Type of admission"
    )
    
    admission_source = models.CharField(
        max_length=50,
        choices=[
            ('OUTPATIENT', 'Outpatient Department'),
            ('EMERGENCY', 'Emergency Department'),
            ('REFERRAL', 'Referred from Another Facility'),
            ('TRANSFER', 'Transfer from Another Ward'),
            ('DIRECT', 'Direct Admission'),
        ],
        default='OUTPATIENT',
        help_text="Source of admission"
    )
    
    admission_date = models.DateTimeField(
        default=timezone.now,
        help_text="Date and time of admission"
    )
    
    admission_status = models.CharField(
        max_length=50,
        choices=[
            ('ADMITTED', 'Admitted'),
            ('DISCHARGED', 'Discharged'),
            ('TRANSFERRED', 'Transferred'),
            ('ABSENT', 'Absent Without Leave'),
        ],
        default='ADMITTED',
        help_text="Current admission status"
    )
    
    discharge_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date and time of discharge (set when discharged)"
    )
    
    discharge_summary = models.OneToOneField(
        'discharges.DischargeSummary',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='linked_admission',
        help_text="Discharge summary linked to this admission"
    )
    
    admitting_doctor = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='admissions_created',
        help_text="Doctor who admitted the patient"
    )
    
    chief_complaint = models.TextField(
        blank=True,
        default='',
        help_text="Chief complaint at admission"
    )
    
    admission_notes = models.TextField(
        blank=True,
        help_text="Additional notes about the admission"
    )
    
    transferred_from = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transfers_to',
        help_text="Previous admission if transferred from another ward/bed"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'admissions'
        ordering = ['-admission_date']
        indexes = [
            models.Index(fields=['visit']),
            models.Index(fields=['ward', 'admission_status']),
            models.Index(fields=['bed', 'admission_status']),
            models.Index(fields=['admission_status']),
            models.Index(fields=['admission_date']),
        ]
        verbose_name = 'Admission'
        verbose_name_plural = 'Admissions'
    
    def __str__(self):
        return f"Admission {self.visit_id} - {self.ward.name} Bed {self.bed.bed_number}"
    
    def clean(self):
        """Validate admission data."""
        # Ensure bed belongs to ward
        if self.bed and self.ward:
            if self.bed.ward_id != self.ward_id:
                raise ValidationError("Bed must belong to the selected ward.")
        
        # Ensure bed is available if creating new admission
        # Note: For new admissions created through the serializer, bed availability
        # is already checked and the bed is marked unavailable BEFORE this clean() is called.
        # So if the bed is unavailable, it's either:
        # 1. We just marked it unavailable (which is fine - no existing admission)
        # 2. It was already unavailable and allocated to another patient (error)
        # We check for existing admissions to distinguish these cases.
        if not self.pk and self.bed and self.bed.pk:
            # Check if this bed is already allocated to another admission
            existing_admission = Admission.objects.filter(
                bed_id=self.bed.pk,
                admission_status='ADMITTED'
            ).exclude(visit=self.visit if self.visit and self.visit.pk else None).first()
            
            if existing_admission:
                raise ValidationError(
                    f"Bed {self.bed.bed_number} is already allocated to another patient."
                )
            
            # If bed is unavailable but not allocated to another admission,
            # it means we just marked it unavailable (which is fine).
            # The serializer already validated availability before marking it unavailable.
        
        # Ensure visit is OPEN when admitting
        if self.visit and self.visit.status != 'OPEN':
            if not self.pk:  # Only check on creation
                raise ValidationError("Can only admit patients with OPEN visits.")
        
        # Validate discharge date is after admission date
        if self.discharge_date and self.admission_date:
            if self.discharge_date < self.admission_date:
                raise ValidationError("Discharge date cannot be before admission date.")
    
    def save(self, *args, **kwargs):
        """Override save to handle bed availability and validation."""
        # Note: Bed availability is primarily handled in:
        # - Serializer.create() for new admissions (with transaction locking)
        # - discharge() method for discharges
        # - transfer() method for transfers
        # This method serves as a safety net for direct model saves
        
        is_new = self.pk is None
        
        if is_new:
            # Mark bed as unavailable when creating admission (safety net if serializer wasn't used)
            if self.bed and self.bed.is_available:
                self.bed.is_available = False
                self.bed.save(update_fields=['is_available', 'updated_at'])
        else:
            # If admission status changed to DISCHARGED or TRANSFERRED, free the bed
            # (This is a backup - primary handling is in discharge() and transfer() methods)
            try:
                old_admission = Admission.objects.get(pk=self.pk)
                if old_admission.admission_status != self.admission_status:
                    if self.admission_status in ['DISCHARGED', 'TRANSFERRED']:
                        if self.bed and not self.bed.is_available:
                            # Only update if bed is still marked as unavailable
                            self.bed.is_available = True
                            self.bed.save(update_fields=['is_available', 'updated_at'])
                    elif old_admission.admission_status in ['DISCHARGED', 'TRANSFERRED']:
                        # Re-admitting to same bed
                        if self.bed and self.bed.is_available:
                            self.bed.is_available = False
                            self.bed.save(update_fields=['is_available', 'updated_at'])
            except Admission.DoesNotExist:
                pass  # Shouldn't happen, but handle gracefully
        
        self.full_clean()
        super().save(*args, **kwargs)
    
    def discharge(self, discharge_date=None):
        """Discharge the patient and free the bed."""
        from django.db import transaction
        
        if self.admission_status == 'DISCHARGED':
            raise ValidationError("Patient is already discharged.")
        
        with transaction.atomic():
            self.admission_status = 'DISCHARGED'
            self.discharge_date = discharge_date or timezone.now()
            
            if self.bed:
                # Lock bed row to prevent race conditions
                bed = Bed.objects.select_for_update().get(pk=self.bed.pk)
                bed.is_available = True
                bed.save(update_fields=['is_available', 'updated_at'])
            
            self.save()
    
    def transfer(self, new_ward, new_bed, transfer_notes=None):
        """Transfer patient to a different ward/bed."""
        from django.db import transaction
        
        if self.admission_status == 'DISCHARGED':
            raise ValidationError("Cannot transfer a discharged patient.")
        
        with transaction.atomic():
            # Lock both beds to prevent race conditions
            old_bed = Bed.objects.select_for_update().get(pk=self.bed.pk) if self.bed else None
            new_bed_locked = Bed.objects.select_for_update().get(pk=new_bed.pk)
            
            # Double-check new bed is still available
            if not new_bed_locked.is_available:
                raise ValidationError(f"Bed {new_bed_locked.bed_number} is not available.")
            
            if not new_bed_locked.is_active:
                raise ValidationError(f"Bed {new_bed_locked.bed_number} is not active.")
            
            # Free old bed
            if old_bed:
                old_bed.is_available = True
                old_bed.save(update_fields=['is_available', 'updated_at'])
            
            # Create transfer record
            transferred_from = self
            
            # Update admission
            self.ward = new_ward
            self.bed = new_bed_locked
            self.admission_status = 'TRANSFERRED'
            if transfer_notes:
                self.admission_notes = f"{self.admission_notes}\n\nTransfer: {transfer_notes}".strip()
            
            # Mark new bed as unavailable
            new_bed_locked.is_available = False
            new_bed_locked.save(update_fields=['is_available', 'updated_at'])
            
            self.save()
            
            # Create new admission record for the transfer
            new_admission = Admission.objects.create(
                visit=self.visit,
                ward=new_ward,
                bed=new_bed_locked,
                admission_type=self.admission_type,
                admission_source='TRANSFER',
                admission_date=timezone.now(),
                admission_status='ADMITTED',
                admitting_doctor=self.admitting_doctor,
                chief_complaint=self.chief_complaint,
                admission_notes=transfer_notes or "Transferred from another ward",
                transferred_from=transferred_from
            )
        
        return new_admission
    
    def get_length_of_stay_days(self):
        """Calculate length of stay in days."""
        end_date = self.discharge_date or timezone.now()
        delta = end_date - self.admission_date
        return delta.days


"""
Patient model - PHI data, strictly protected.

Per EMR Rules:
- Patient data is PHI (Protected Health Information)
- Must be encrypted at rest
- Never logged in plaintext
- Receptionist can register patients
- All clinical actions require a Visit (visit-scoped)
"""
from django.db import models
from django.core.exceptions import ValidationError


class Patient(models.Model):
    """
    Patient model - stores PHI (Protected Health Information).
    
    Design Principles:
    1. All fields are PHI and must be protected
    2. Soft-delete only (no hard delete for compliance)
    3. Unique identifiers for patient matching
    4. Audit timestamps for compliance
    """
    
    # Patient identifiers (PHI)
    first_name = models.CharField(
        max_length=255,
        help_text="Patient first name (PHI)"
    )
    
    last_name = models.CharField(
        max_length=255,
        help_text="Patient last name (PHI)"
    )
    
    middle_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Patient middle name (PHI)"
    )
    
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        help_text="Patient date of birth (PHI)"
    )
    
    gender = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[
            ('MALE', 'Male'),
            ('FEMALE', 'Female'),
            ('OTHER', 'Other'),
            ('PREFER_NOT_TO_SAY', 'Prefer not to say'),
        ],
        help_text="Patient gender"
    )
    
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Patient phone number (PHI)"
    )
    
    email = models.EmailField(
        blank=True,
        null=True,
        help_text="Patient email address (PHI)"
    )
    
    address = models.TextField(
        blank=True,
        null=True,
        help_text="Patient address (PHI)"
    )
    
    # Emergency Contact Information
    emergency_contact_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Emergency contact name (PHI)"
    )
    
    emergency_contact_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Emergency contact phone number (PHI)"
    )
    
    emergency_contact_relationship = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Relationship to patient (e.g., Spouse, Parent, Sibling, Friend)"
    )
    
    national_id = models.CharField(
        max_length=50,
        blank=True,
        unique=True,
        null=True,
        help_text="National ID number (PHI, unique)"
    )
    national_health_id = models.CharField(
        max_length=50,
        blank=True,
        unique=True,
        null=True,
        help_text="National Health ID (e.g. NIN/NHIA Nigeria); unique, nullable"
    )
    id_verified = models.BooleanField(
        default=False,
        help_text="Whether National Health ID has been verified via external check"
    )
    
    patient_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="Internal patient ID (unique identifier, auto-generated)"
    )
    
    # Medical information
    blood_group = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        choices=[
            ('A+', 'A+'),
            ('A-', 'A-'),
            ('B+', 'B+'),
            ('B-', 'B-'),
            ('AB+', 'AB+'),
            ('AB-', 'AB-'),
            ('O+', 'O+'),
            ('O-', 'O-'),
        ],
        help_text="Blood group"
    )
    
    allergies = models.TextField(
        blank=True,
        null=True,
        help_text="Known allergies (PHI)"
    )
    
    medical_history = models.TextField(
        blank=True,
        null=True,
        help_text="Medical history summary (PHI)"
    )
    
    # Soft delete
    is_active = models.BooleanField(
        default=True,
        help_text="Soft delete flag. False means patient record is archived."
    )
    
    # Patient Portal Access Control
    portal_enabled = models.BooleanField(
        default=False,
        help_text="Whether patient portal access is enabled for this patient"
    )
    
    # Patient Portal Verification
    is_verified = models.BooleanField(
        default=False,
        help_text="Whether the patient account has been verified by a Receptionist. Patients must be verified before accessing the portal."
    )
    
    verified_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_patients',
        help_text="Receptionist who verified this patient account"
    )
    
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when patient account was verified"
    )
    
    # Patient Portal Access
    user = models.OneToOneField(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='patient_profile',
        help_text="User account for patient portal access (optional)"
    )
    
    # Retainership fields
    has_retainership = models.BooleanField(
        default=False,
        help_text="Whether patient has an active retainership agreement"
    )
    
    retainership_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Type of retainership (e.g., 'Monthly', 'Quarterly', 'Annual', 'Corporate')"
    )
    
    retainership_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Retainership start date"
    )
    
    retainership_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Retainership end date (if applicable)"
    )
    
    retainership_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Retainership amount paid"
    )
    
    # Audit timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When patient was registered"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When patient record was last updated"
    )
    
    class Meta:
        db_table = 'patients'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient_id']),
            models.Index(fields=['national_id']),
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['phone']),
            models.Index(fields=['is_active']),
            # Note: is_verified index will be added after migration
        ]
        verbose_name = 'Patient'
        verbose_name_plural = 'Patients'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.patient_id})"
    
    def get_full_name(self):
        """Get patient's full name."""
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        return ' '.join(parts)
    
    def get_age(self):
        """Calculate patient age from date of birth."""
        if not self.date_of_birth:
            return None
        
        from django.utils import timezone
        today = timezone.now().date()
        age = today.year - self.date_of_birth.year
        if today.month < self.date_of_birth.month or \
           (today.month == self.date_of_birth.month and today.day < self.date_of_birth.day):
            age -= 1
        return age
    
    @classmethod
    def generate_patient_id(cls):
        """
        Generate the next sequential patient ID in format LMC000001.
        
        Returns:
            str: Next available patient ID (e.g., LMC000001, LMC000002, etc.)
        """
        # Find all existing patient_ids that start with "LMC"
        existing_ids = cls.objects.filter(patient_id__startswith='LMC').values_list('patient_id', flat=True)
        
        max_number = 0
        for patient_id in existing_ids:
            try:
                # Extract numeric part (everything after "LMC")
                numeric_part = patient_id[3:]  # Skip "LMC" prefix
                number = int(numeric_part)
                max_number = max(max_number, number)
            except (ValueError, IndexError):
                # Skip invalid formats
                continue
        
        # Increment and format with 6 leading zeros
        next_number = max_number + 1
        return f"LMC{next_number:06d}"
    
    def clean(self):
        """Validate patient data."""
        # Ensure patient_id is set (auto-generated if not provided)
        if not self.patient_id:
            # Generate sequential patient ID in format LMC000001
            self.patient_id = self.generate_patient_id()
    
    def save(self, *args, **kwargs):
        """Override save to run validation and ensure patient_id."""
        # Generate patient_id if not set (only for new instances)
        # Note: Serializer should set patient_id before calling save(),
        # but this is a fallback for direct model usage
        if not self.pk and not self.patient_id:
            self.clean()
        # Run full_clean for validation (skip if patient_id not set - serializer will handle it)
        try:
            if self.patient_id:
                self.full_clean()
        except ValidationError as e:
            # Re-raise validation errors
            raise
        super().save(*args, **kwargs)

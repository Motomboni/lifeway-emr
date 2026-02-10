"""
Appointment model - for scheduling patient appointments.

Per EMR Rules:
- Appointments are scheduled before visits
- Receptionist can create/manage appointments
- Doctors can view their own appointments
- Appointments can be linked to visits (optional)
- Status tracking: SCHEDULED, CONFIRMED, COMPLETED, CANCELLED, NO_SHOW
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class Appointment(models.Model):
    """
    Appointment model - for scheduling patient appointments.
    
    Design Principles:
    1. ForeignKey to Patient - required
    2. ForeignKey to Doctor (User) - required
    3. ForeignKey to Visit - optional (linked when visit is created)
    4. Receptionist creates/manages appointments
    5. Status tracking for appointment lifecycle
    6. Audit logging mandatory
    """
    
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('CONFIRMED', 'Confirmed'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('NO_SHOW', 'No Show'),
    ]
    
    # Core relationships
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='appointments',
        help_text="Patient for this appointment"
    )
    
    doctor = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='appointments',
        help_text="Doctor assigned to this appointment. PROTECT prevents deletion."
    )
    
    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.SET_NULL,
        related_name='appointments',
        null=True,
        blank=True,
        help_text="Visit linked to this appointment (optional, set when visit is created)"
    )
    
    # Appointment details
    appointment_date = models.DateTimeField(
        help_text="Date and time of the appointment"
    )
    
    duration_minutes = models.IntegerField(
        default=30,
        help_text="Duration of appointment in minutes"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='SCHEDULED',
        help_text="Status of the appointment"
    )
    
    reason = models.TextField(
        blank=True,
        help_text="Reason for appointment or chief complaint"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about the appointment"
    )
    
    # User tracking
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='appointments_created',
        help_text="User who created this appointment. PROTECT prevents deletion."
    )
    
    # Audit timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the appointment was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the appointment was last updated"
    )
    
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the appointment was cancelled"
    )
    
    cancelled_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='appointments_cancelled',
        null=True,
        blank=True,
        help_text="User who cancelled this appointment"
    )
    
    cancellation_reason = models.TextField(
        blank=True,
        help_text="Reason for cancellation"
    )
    
    class Meta:
        db_table = 'appointments'
        ordering = ['appointment_date']
        indexes = [
            models.Index(fields=['patient']),
            models.Index(fields=['doctor']),
            models.Index(fields=['appointment_date']),
            models.Index(fields=['status']),
            models.Index(fields=['visit']),
        ]
        verbose_name = 'Appointment'
        verbose_name_plural = 'Appointments'
    
    def __str__(self):
        return f"Appointment {self.id} - {self.patient.full_name} with Dr. {self.doctor.get_full_name()} on {self.appointment_date}"
    
    def clean(self):
        """
        Validation: Ensure appointment can be created/updated.
        
        Rules:
        1. Doctor must have DOCTOR role
        2. Appointment date must be in the future (for new appointments)
        3. Duration must be positive
        4. Visit must belong to same patient (if linked)
        """
        # 1️⃣ Doctor must have DOCTOR role
        if self.doctor_id:
            user_role = getattr(self.doctor, 'role', None)
            if not user_role:
                user_role = getattr(self.doctor, 'get_role', lambda: None)()
            
            if user_role != 'DOCTOR':
                raise ValidationError("Appointment doctor must have DOCTOR role.")
        
        # 2️⃣ Appointment date must be in the future (for new appointments)
        if not self.pk and self.appointment_date:
            if self.appointment_date <= timezone.now():
                raise ValidationError("Appointment date must be in the future.")
        
        # 3️⃣ Duration must be positive
        if self.duration_minutes and self.duration_minutes <= 0:
            raise ValidationError("Appointment duration must be positive.")
        
        # 4️⃣ Visit must belong to same patient (if linked)
        if self.visit_id and self.patient_id:
            if self.visit.patient_id != self.patient_id:
                raise ValidationError("Visit must belong to the same patient as the appointment.")
    
    def save(self, *args, **kwargs):
        """Override save to run clean() validation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def is_past(self):
        """Check if appointment date is in the past."""
        return self.appointment_date < timezone.now()
    
    @property
    def is_upcoming(self):
        """Check if appointment is upcoming (not past, not completed/cancelled)."""
        return (
            not self.is_past and
            self.status in ['SCHEDULED', 'CONFIRMED']
        )

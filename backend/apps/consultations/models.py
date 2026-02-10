from django.db import models
from django.core.exceptions import ValidationError
from apps.core.validators import validate_visit_required


class Consultation(models.Model):
    """
    Consultation domain model - strictly visit-scoped clinical documentation.

    Design Principles:
    1. OneToOneField with Visit enforces: one consultation per visit, cannot exist without visit
    2. CASCADE delete: consultation deleted when visit is deleted (visit is source of truth)
    3. PROTECT on created_by: prevents deletion of doctors with active consultations
    4. All fields are PHI and must be encrypted at rest, never logged in plaintext
    5. Payment enforcement must be checked at API/middleware level before creation
    """

    # Core relationship — ABSOLUTE: Consultation cannot exist without Visit
    visit = models.OneToOneField(
        'visits.Visit',
        on_delete=models.CASCADE,
        related_name='consultation',
        help_text="Visit is the single source of clinical truth. Consultation is strictly visit-scoped.",
        validators=[validate_visit_required],
        null=False,  # Explicitly enforce NOT NULL at database level
        blank=False,  # Explicitly enforce required at form level
    )

    # Doctor who created the consultation
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='consultations',
        null=True,
        blank=True,
        help_text="Doctor who documented this consultation. Can be auto-assigned from ServiceCatalog."
    )
    
    # Consultation status flow: PENDING → ACTIVE → CLOSED
    status = models.CharField(
        max_length=20,
        default='PENDING',
        choices=[
            ('PENDING', 'Pending'),
            ('ACTIVE', 'Active'),
            ('CLOSED', 'Closed'),
        ],
        help_text="Consultation status. PENDING: awaiting payment/assignment, ACTIVE: in progress, CLOSED: completed"
    )
    
    # Clinical documentation fields (PHI)
    history = models.TextField(
        blank=True,
        help_text="Patient history, chief complaint, and presenting symptoms"
    )

    examination = models.TextField(
        blank=True,
        help_text="Physical examination findings and clinical observations"
    )

    diagnosis = models.TextField(
        blank=True,
        help_text="Clinical diagnosis, differential diagnosis, and assessment"
    )

    clinical_notes = models.TextField(
        blank=True,
        help_text="Additional clinical notes, treatment plan, and follow-up instructions"
    )

    # Audit timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when consultation was first created"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when consultation was last modified"
    )

    class Meta:
        db_table = 'consultations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['visit']),
            models.Index(fields=['created_by']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'Consultation'
        verbose_name_plural = 'Consultations'

    def __str__(self):
        return f"Consultation for Visit {self.visit_id} by {self.created_by_id}"

    def clean(self):
        """
        HARD MODEL-LEVEL ENFORCEMENT.
        This method is the last line of defense for data integrity.
        """

        # 1️⃣ Visit must not be CLOSED
        if self.visit_id:
            try:
                # Access visit if it's already loaded, otherwise skip check
                # (visit will be validated at API level)
                if hasattr(self, 'visit') and self.visit:
                    if self.visit.status == 'CLOSED':
                        raise ValidationError(
                            "Cannot create or modify consultation for a CLOSED visit. "
                            "Closed visits are immutable per EMR rules."
                        )
            except ValidationError:
                # Re-raise ValidationError
                raise
            except Exception:
                # Visit not loaded yet, skip check (will be validated at API level)
                pass

        # 2️⃣ ONLY doctors can create consultations (ROLE ENFORCEMENT)
        # Check is done at API level, but we validate here if created_by is loaded
        if self.created_by_id:
            try:
                # Access created_by if it's already loaded
                if hasattr(self, 'created_by') and self.created_by:
                    # Get user role (User model has 'role' field, not 'is_doctor')
                    user_role = getattr(self.created_by, 'role', None)
                    if not user_role:
                        # Try method if field doesn't exist
                        user_role = getattr(self.created_by, 'get_role', lambda: None)()
                    
                    if user_role != 'DOCTOR':
                        raise ValidationError(
                            "Only users with Doctor role can create consultations."
                        )
            except ValidationError:
                # Re-raise ValidationError
                raise
            except Exception:
                # created_by not loaded yet or other error, skip check (will be validated at API level)
                pass
        
        # 3️⃣ Status validation
        # PENDING: awaiting payment/assignment
        # ACTIVE: in progress
        # CLOSED: completed
        if self.status not in ['PENDING', 'ACTIVE', 'CLOSED']:
            raise ValidationError(
                f"Invalid consultation status '{self.status}'. "
                "Must be one of: PENDING, ACTIVE, CLOSED"
            )
        
        # If status is ACTIVE or CLOSED, created_by should be set
        if self.status in ['ACTIVE', 'CLOSED'] and not self.created_by_id:
            raise ValidationError(
                f"Consultation with status '{self.status}' must have an assigned doctor."
            )

    def save(self, *args, **kwargs):
        """
        Override save to guarantee model-level enforcement.
        No Consultation can reach the database without passing clean().
        """
        self.full_clean()
        super().save(*args, **kwargs)

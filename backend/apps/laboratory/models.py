from django.db import models
from django.core.exceptions import ValidationError

# Import catalog models for easy access
from .catalog_models import LabTestCatalog
from apps.core.validators import validate_consultation_required, validate_active_lab_order


class LabOrder(models.Model):
    """
    LabOrder = clinical intent to investigate.
    Results live in LabResult.
    """
    
    class Status(models.TextChoices):
        ORDERED = "ORDERED", "Ordered"
        SAMPLE_COLLECTED = "SAMPLE_COLLECTED", "Sample Collected"
        RESULT_READY = "RESULT_READY", "Result Ready"

    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.PROTECT,
        related_name='lab_orders',
        help_text="Visit is the single source of clinical truth. Lab order is visit-scoped."
    )

    consultation = models.ForeignKey(
        'consultations.Consultation',
        on_delete=models.PROTECT,
        related_name='lab_orders',
        help_text="Consultation this lab order belongs to. Lab orders require consultation context.",
        validators=[validate_consultation_required],
        null=False,  # Explicitly enforce NOT NULL at database level
        blank=False,  # Explicitly enforce required at form level
    )

    ordered_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='lab_orders_created',
        help_text="Doctor who ordered the lab tests. PROTECT prevents deletion."
    )

    tests_requested = models.JSONField(
        help_text="List of tests requested (JSON array of test names/codes)"
    )
    
    clinical_indication = models.TextField(
        blank=True,
        help_text="Clinical reason for ordering tests"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ORDERED,
        help_text="Status of the lab order"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the lab order was created"
    )

    class Meta:
        db_table = 'lab_orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['visit']),
            models.Index(fields=['consultation']),
            models.Index(fields=['status']),
            models.Index(fields=['ordered_by']),
        ]
        verbose_name = 'Lab Order'
        verbose_name_plural = 'Lab Orders'

    def __str__(self):
        return f"Lab Order {self.id} for Visit {self.visit_id}"

    def clean(self):
        """
        Validation: Ensure lab order can be created.
        
        Nigerian Clinic Governance Rules:
        1. Consultation is REQUIRED (enforced at database level)
        2. Visit must be OPEN (not CLOSED)
        3. Consultation must belong to same visit
        4. Only doctors can order labs
        5. Payment must be CLEARED
        """
        if not self.visit_id:
            return
        
        visit = self.visit

        # ❌ GOVERNANCE RULE: Consultation is REQUIRED
        if not self.consultation_id:
            raise ValidationError(
                "Lab orders require a consultation. "
                "Per Nigerian clinic operational rules, all lab orders must have clinical context from a consultation. "
                "Please ensure a consultation exists for this visit."
            )

        # ❌ Closed visit immutability
        if visit.status == 'CLOSED':
            raise ValidationError(
                "Cannot create LabOrder on a closed visit. "
                "Closed visits are immutable per EMR governance rules."
            )

        # ❌ Consultation must belong to same visit
        if self.consultation.visit_id != self.visit_id:
            raise ValidationError(
                "Consultation does not belong to this Visit. "
                "Consultation ID: %(consultation_id)s belongs to Visit ID: %(visit_id)s, "
                "but this LabOrder is for Visit ID: %(current_visit_id)s."
            ) % {
                'consultation_id': self.consultation_id,
                'visit_id': self.consultation.visit_id,
                'current_visit_id': self.visit_id,
            }

        # ❌ Doctor-only ordering
        # Check role attribute (consistent with codebase patterns)
        user_role = getattr(self.ordered_by, 'role', None)
        if not user_role:
            # Fallback to property if exists
            user_role = getattr(self.ordered_by, 'get_role', lambda: None)()
        
        if user_role != 'DOCTOR':
            raise ValidationError(
                f"Only doctors can create lab orders. "
                f"User role '{user_role}' is not authorized to order lab tests. "
                f"Please contact a doctor to place this order."
            )

        # ❌ Payment enforcement
        if not visit.is_payment_cleared():
            raise ValidationError(
                f"Payment must be cleared before lab ordering. "
                f"Current payment status: {visit.payment_status}. "
                f"Please process payment before placing lab orders."
            )

    def save(self, *args, **kwargs):
        """Override save to run clean() validation."""
        self.full_clean()
        super().save(*args, **kwargs)


class LabResult(models.Model):
    """
    LabResult = immutable outcome of a LabOrder.
    Created ONLY by Lab Tech.
    """

    ABNORMALITY_CHOICES = [
        ('NORMAL', 'Normal'),
        ('ABNORMAL', 'Abnormal'),
        ('CRITICAL', 'Critical'),
    ]

    lab_order = models.OneToOneField(
        'laboratory.LabOrder',
        on_delete=models.CASCADE,
        related_name='result',
        help_text="Lab order this result belongs to. One result per order.",
        null=False,  # Explicitly enforce NOT NULL at database level
        blank=False,  # Explicitly enforce required at form level
    )

    result_data = models.TextField(
        help_text="Raw lab findings. No diagnosis or interpretation."
    )

    abnormal_flag = models.CharField(
        max_length=10,
        choices=ABNORMALITY_CHOICES,
        default='NORMAL',
        help_text="Abnormality flag for the result"
    )

    recorded_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='lab_results_recorded',
        help_text="Lab Tech who recorded this result. PROTECT prevents deletion."
    )

    recorded_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the result was recorded"
    )

    class Meta:
        db_table = 'lab_results'
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['lab_order']),
            models.Index(fields=['recorded_by']),
            models.Index(fields=['recorded_at']),
        ]
        verbose_name = 'Lab Result'
        verbose_name_plural = 'Lab Results'

    def __str__(self):
        return f"LabResult for Order {self.lab_order_id}"

    def clean(self):
        """
        Validation: Ensure lab result can be recorded.
        
        Nigerian Clinic Governance Rules:
        1. LabOrder is REQUIRED (enforced at database level)
        2. LabOrder must be ACTIVE (ORDERED or SAMPLE_COLLECTED)
        3. Visit must be OPEN (not CLOSED)
        4. Payment must be CLEARED
        5. Only Lab Tech can record results
        6. Lab results are immutable once recorded
        """
        if not self.lab_order_id:
            raise ValidationError(
                "Lab result requires an active lab order. "
                "Per Nigerian clinic operational rules, results can only be posted for active orders."
            )
        
        visit = self.lab_order.visit

        # ❌ GOVERNANCE RULE: LabOrder must be ACTIVE
        # Use validator for consistency
        validate_active_lab_order(self.lab_order)

        # 1️⃣ Visit must be OPEN (not CLOSED)
        if visit.status == 'CLOSED':
            raise ValidationError(
                "Cannot record lab result for CLOSED visit. "
                "Visit ID: %(visit_id)s is CLOSED. Closed visits are immutable per EMR governance rules."
            ) % {'visit_id': visit.id}

        # 2️⃣ Payment must be CLEARED
        if not visit.is_payment_cleared():
            raise ValidationError(
                f"Cannot record lab result before payment clearance. "
                f"Current payment status: {visit.payment_status}. "
                f"Please ensure payment is cleared before posting lab results."
            )

        # 4️⃣ ONLY Lab Tech can record results
        # Check role attribute (consistent with codebase patterns)
        user_role = getattr(self.recorded_by, 'role', None)
        if not user_role:
            # Fallback to property if exists
            user_role = getattr(self.recorded_by, 'get_role', lambda: None)()
        
        if user_role != 'LAB_TECH':
            raise ValidationError(
                f"Only Lab Technicians can record lab results. "
                f"User role '{user_role}' is not authorized. "
                f"Please contact a Lab Technician to post this result."
            )

        # 5️⃣ Enforce immutability
        if self.pk:
            raise ValidationError(
                f"Lab results are immutable once recorded. "
                f"Result ID: {self.pk} cannot be modified. "
                f"If correction is needed, please contact system administrator."
            )

    def save(self, *args, **kwargs):
        """Override save to run clean() validation."""
        self.full_clean()
        super().save(*args, **kwargs)

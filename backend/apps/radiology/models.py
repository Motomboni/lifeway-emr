"""
Radiology models.

RadiologyRequest is the single source of truth for Service Catalog radiology orders.
- All reports for this flow are stored directly on RadiologyRequest (report, report_date,
  reported_by, image_count). Do NOT create RadiologyResult for Service Catalog orders.
- RadiologyResult is used only for the legacy RadiologyOrder flow (RadiologyOrder →
  RadiologyResult). Service Catalog orders use RadiologyRequest only.
"""
from django.db import models
from django.core.exceptions import ValidationError

# Import study types models for easy access
from .study_types_models import RadiologyStudyType
from apps.core.validators import validate_consultation_required, validate_active_radiology_request


class RadiologyRequest(models.Model):
    """
    Radiology Request model - visit-scoped and consultation-dependent.
    
    Design Principles:
    1. ForeignKey to Visit - visit-scoped
    2. ForeignKey to Consultation - consultation-dependent (REQUIRED)
    3. Doctor creates requests (ordered_by)
    4. Radiology Tech uploads reports (reported_by)
    5. Status tracking: PENDING, IN_PROGRESS, COMPLETED, CANCELLED
    6. Image metadata only (no raw DICOM for now)
    """
    
    # Core relationships - ABSOLUTE: Cannot exist without Visit and Consultation
    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.CASCADE,
        related_name='radiology_requests',
        help_text="Visit is the single source of clinical truth. Radiology request is visit-scoped."
    )
    
    consultation = models.ForeignKey(
        'consultations.Consultation',
        on_delete=models.CASCADE,
        related_name='radiology_requests',
        help_text="Radiology request requires consultation context. Cannot exist without consultation.",
        validators=[validate_consultation_required],
        null=False,  # Explicitly enforce NOT NULL at database level
        blank=False,  # Explicitly enforce required at form level
    )
    
    # Radiology study information
    study_type = models.CharField(
        max_length=255,
        blank=True,
        default='General Study',
        help_text="Type of radiology study requested (e.g., 'Chest X-Ray', 'CT Scan Head')"
    )
    
    study_code = models.CharField(
        max_length=100,
        blank=True,
        help_text="Radiology study code/identifier"
    )
    
    clinical_indication = models.TextField(
        blank=True,
        help_text="Clinical indication for the radiology study"
    )
    
    instructions = models.TextField(
        blank=True,
        help_text="Special instructions for the radiology study"
    )
    
    # Status tracking (PENDING | COMPLETED only for Service Catalog flow)
    status = models.CharField(
        max_length=20,
        default='PENDING',
        choices=[
            ('PENDING', 'Pending'),
            ('COMPLETED', 'Completed'),
        ],
        help_text="Status of the radiology request (PENDING until report is posted)"
    )
    
    # Report (Radiology Tech only)
    report = models.TextField(
        null=True,
        blank=True,
        help_text="Radiology report/interpretation (PHI - only Radiology Tech can update)"
    )
    
    finding_flag = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=[
            ('NORMAL', 'Normal'),
            ('ABNORMAL', 'Abnormal'),
            ('CRITICAL', 'Critical Finding'),
        ],
        help_text="Finding flag set by Radiology Tech when posting report"
    )
    
    report_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the report was posted"
    )
    
    # Image metadata (no raw DICOM for now)
    image_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Number of images in the study"
    )
    
    image_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Image metadata (e.g., modality, series, slices) - no raw DICOM"
    )
    
    # User tracking
    ordered_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='radiology_requests_ordered',
        help_text="Doctor who ordered the study"
    )
    
    reported_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='radiology_requests_reported',
        null=True,
        blank=True,
        help_text="Radiology Tech who posted the report"
    )
    
    # Audit timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the radiology request was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the radiology request was last updated"
    )
    
    class Meta:
        db_table = 'radiology_requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['visit']),
            models.Index(fields=['consultation']),
            models.Index(fields=['status']),
            models.Index(fields=['ordered_by']),
        ]
        verbose_name = 'Radiology Request'
        verbose_name_plural = 'Radiology Requests'
    
    def __str__(self):
        return f"Radiology Request {self.study_type} for Visit {self.visit.id}"
    
    def clean(self):
        """
        Validation: Ensure consultation exists and visit is not CLOSED.
        
        Nigerian Clinic Governance Rules:
        1. Consultation is REQUIRED (enforced at database level)
        2. Visit must not be CLOSED
        3. Consultation must belong to same visit
        4. Only doctors can order radiology studies
        5. Payment must be cleared (for standard orders)
        """
        if not self.visit_id:
            return
        
        visit = self.visit
        
        # ❌ GOVERNANCE RULE: Consultation is REQUIRED
        if not self.consultation_id:
            raise ValidationError(
                "Radiology requests require a consultation. "
                "Per Nigerian clinic operational rules, all radiology requests must have clinical context from a consultation. "
                "Please ensure a consultation exists for this visit."
            )
        
        # ❌ Closed visit immutability
        if visit.status == 'CLOSED':
            raise ValidationError(
                "Cannot create or modify radiology request for a CLOSED visit. "
                "Visit ID: %(visit_id)s is CLOSED. Closed visits are immutable per EMR governance rules."
            ) % {'visit_id': visit.id}
        
        # ❌ Consultation must belong to same visit
        if self.consultation.visit_id != self.visit_id:
            raise ValidationError(
                "Consultation must belong to the same visit as the radiology request. "
                "Consultation ID: %(consultation_id)s belongs to Visit ID: %(visit_id)s, "
                "but this RadiologyRequest is for Visit ID: %(current_visit_id)s."
            ) % {
                'consultation_id': self.consultation_id,
                'visit_id': self.consultation.visit_id,
                'current_visit_id': self.visit_id,
            }
        
        # ❌ Doctor-only ordering
        if self.ordered_by_id:
            user_role = getattr(self.ordered_by, 'role', None)
            if not user_role:
                user_role = getattr(self.ordered_by, 'get_role', lambda: None)()
            
            if user_role != 'DOCTOR':
                raise ValidationError(
                    f"Only doctors can order radiology studies. "
                    f"User role '{user_role}' is not authorized to order radiology studies. "
                    f"Please contact a doctor to place this order."
                )
        
        # ❌ Payment enforcement (standard flow)
        # Note: Emergency override can be added if needed
        if not visit.is_payment_cleared():
            raise ValidationError(
                f"Payment must be cleared before ordering radiology studies. "
                f"Current payment status: {visit.payment_status}. "
                f"Please process payment before placing radiology orders."
            )
    
    def save(self, *args, **kwargs):
        """Override save to run clean() validation."""
        self.full_clean()
        super().save(*args, **kwargs)


class RadiologyOrder(models.Model):
    """
    RadiologyOrder = intent to perform diagnostic imaging.
    Results and images live in RadiologyResult.
    """

    IMAGING_CHOICES = [
        ('XRAY', 'X-Ray'),
        ('CT', 'CT Scan'),
        ('MRI', 'MRI'),
        ('US', 'Ultrasound'),
    ]

    PRIORITY_CHOICES = [
        ('ROUTINE', 'Routine'),
        ('URGENT', 'Urgent'),
    ]

    STATUS_CHOICES = [
        ('ORDERED', 'Ordered'),
        ('SCHEDULED', 'Scheduled'),
        ('PERFORMED', 'Performed'),
        ('CANCELLED', 'Cancelled'),
    ]

    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.CASCADE,
        related_name='radiology_orders',
        help_text="Visit is the single source of clinical truth. Radiology order is visit-scoped."
    )

    ordered_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='radiology_orders_created',
        help_text="Doctor who ordered the radiology study. PROTECT prevents deletion."
    )

    imaging_type = models.CharField(
        max_length=10,
        choices=IMAGING_CHOICES,
        help_text="Type of imaging study"
    )

    body_part = models.CharField(
        max_length=100,
        help_text="Body part to be imaged"
    )

    clinical_indication = models.TextField(
        help_text="Reason for imaging request"
    )

    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='ROUTINE',
        help_text="Priority level of the order"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ORDERED',
        help_text="Status of the radiology order"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the radiology order was created"
    )

    class Meta:
        db_table = 'radiology_orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['visit']),
            models.Index(fields=['status']),
            models.Index(fields=['ordered_by']),
            models.Index(fields=['imaging_type']),
        ]
        verbose_name = 'Radiology Order'
        verbose_name_plural = 'Radiology Orders'

    def __str__(self):
        return f"Radiology Order {self.imaging_type} - {self.body_part} for Visit {self.visit_id}"

    def clean(self):
        """
        Validation: Ensure radiology order can be created.
        
        Per EMR Context Document v2:
        - No Consultation → No Radiology Orders
        - Requires Visit + Consultation
        - Ordered only by Doctor
        
        Rules:
        1. Visit must be OPEN (not CLOSED)
        2. Consultation MUST exist (governance rule)
        3. Payment must be CLEARED
        4. Only doctors can order radiology
        """
        if not self.visit_id:
            return
        
        visit = self.visit

        # ❌ GOVERNANCE RULE: Consultation MUST exist
        # Per EMR Context Document v2: "No Consultation → No Lab / Radiology / Drug / Procedure Orders"
        if not hasattr(visit, 'consultation') or not visit.consultation:
            raise ValidationError(
                "Radiology orders require an existing Consultation. "
                "Per EMR governance rules, all radiology orders must have clinical context from a consultation. "
                "Please ensure a consultation exists for this visit."
            )

        # 1️⃣ Visit must be OPEN (not CLOSED)
        if visit.status == 'CLOSED':
            raise ValidationError(
                "Cannot order radiology for a CLOSED visit. "
                "Visit ID: %(visit_id)s is CLOSED. Closed visits are immutable per EMR governance rules."
            ) % {'visit_id': visit.id}

        # 3️⃣ Payment MUST be cleared
        if not visit.is_payment_cleared():
            raise ValidationError(
                "Radiology orders require payment clearance. "
                "Current payment status: %(status)s. "
                "Please process payment before placing radiology orders."
            ) % {'status': visit.payment_status}

        # 4️⃣ ONLY doctors can order radiology
        # Check role attribute (consistent with codebase patterns)
        user_role = getattr(self.ordered_by, 'role', None)
        if not user_role:
            # Fallback to property if exists
            user_role = getattr(self.ordered_by, 'get_role', lambda: None)()
        
        if user_role != 'DOCTOR':
            raise ValidationError(
                "Only doctors can create radiology orders. "
                "User role '%(role)s' is not authorized to order radiology studies. "
                "Please contact a doctor to place this order."
            ) % {'role': user_role}

    def save(self, *args, **kwargs):
        """Override save to run clean() validation."""
        self.full_clean()
        super().save(*args, **kwargs)


class RadiologyResult(models.Model):
    """
    Immutable outcome of a legacy RadiologyOrder (RadiologyOrder → RadiologyResult).
    Created only by Radiology Tech. Not used for Service Catalog radiology orders—
    for those, reports are stored directly on RadiologyRequest.
    """

    FINDING_CHOICES = [
        ('NORMAL', 'Normal'),
        ('ABNORMAL', 'Abnormal'),
        ('CRITICAL', 'Critical Finding'),
    ]

    radiology_order = models.OneToOneField(
        'radiology.RadiologyOrder',
        on_delete=models.CASCADE,
        related_name='result',
        help_text="Radiology order this result belongs to. One result per order."
    )

    report = models.TextField(
        help_text="Radiology report/interpretation. No diagnosis or clinical interpretation."
    )

    finding_flag = models.CharField(
        max_length=10,
        choices=FINDING_CHOICES,
        default='NORMAL',
        help_text="Finding flag for the result"
    )

    image_count = models.IntegerField(
        default=0,
        help_text="Number of images in the study"
    )

    image_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Image metadata (e.g., modality, series, slices) - no raw DICOM"
    )

    reported_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='radiology_results_reported',
        help_text="Radiology Tech who reported this result. PROTECT prevents deletion."
    )

    reported_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the result was reported"
    )

    class Meta:
        db_table = 'radiology_results'
        ordering = ['-reported_at']
        indexes = [
            models.Index(fields=['radiology_order']),
            models.Index(fields=['reported_by']),
            models.Index(fields=['reported_at']),
        ]
        verbose_name = 'Radiology Result'
        verbose_name_plural = 'Radiology Results'

    def __str__(self):
        return f"RadiologyResult for Order {self.radiology_order_id}"

    def clean(self):
        """
        Validation: Ensure radiology result can be recorded.
        
        Rules:
        1. Visit must be OPEN (not CLOSED)
        2. Payment must be CLEARED
        3. RadiologyOrder must be ORDERED or PERFORMED
        4. Only Radiology Tech can record results
        5. Radiology results are immutable once recorded
        """
        if not self.radiology_order_id:
            return
        
        visit = self.radiology_order.visit

        # 1️⃣ Visit must be OPEN (not CLOSED)
        if visit.status == 'CLOSED':
            raise ValidationError("Cannot record radiology result for CLOSED visit.")

        # 2️⃣ Payment must be CLEARED
        if not visit.is_payment_cleared():
            raise ValidationError("Cannot record radiology result before payment clearance.")

        # 3️⃣ RadiologyOrder must be ORDERED or PERFORMED
        if self.radiology_order.status not in ['ORDERED', 'PERFORMED']:
            raise ValidationError(
                "Radiology result can only be recorded for ORDERED or PERFORMED radiology orders."
            )

        # 4️⃣ ONLY Radiology Tech can record results
        # Check role attribute (consistent with codebase patterns)
        user_role = getattr(self.reported_by, 'role', None)
        if not user_role:
            # Fallback to property if exists
            user_role = getattr(self.reported_by, 'get_role', lambda: None)()
        
        if user_role != 'RADIOLOGY_TECH':
            raise ValidationError("Only Radiology Technicians can record radiology results.")

        # 5️⃣ Enforce immutability
        if self.pk:
            raise ValidationError("Radiology results are immutable once recorded.")

    def save(self, *args, **kwargs):
        """Override save to run clean() validation."""
        self.full_clean()
        super().save(*args, **kwargs)

"""
Visit model - the single source of clinical truth.

Per EMR Rules:
- Visit is the container for all clinical actions
- Visit status: OPEN or CLOSED
- Once CLOSED, visit is immutable
- Visit must have consultation before closure
"""
from django.db import models
from django.core.exceptions import ValidationError


# Import here to avoid circular import
def get_consultation_model():
    """Get Consultation model to avoid circular imports."""
    from apps.consultations.models import Consultation
    return Consultation


class Visit(models.Model):
    """
    Visit model - the single source of clinical truth.
    
    All clinical actions (consultation, lab orders, radiology, prescriptions)
    are scoped to a Visit.
    """
    
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='visits',
        help_text="Patient for this visit"
    )
    
    visit_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ('CONSULTATION', 'Consultation'),
            ('FOLLOW_UP', 'Follow-up'),
            ('EMERGENCY', 'Emergency'),
            ('ROUTINE', 'Routine'),
            ('SPECIALIST', 'Specialist'),
        ],
        help_text="Type of visit"
    )
    
    chief_complaint = models.TextField(
        blank=True,
        null=True,
        help_text="Chief complaint or reason for visit"
    )
    
    appointment = models.ForeignKey(
        'appointments.Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='visits',
        help_text="Linked appointment (optional)"
    )
    
    status = models.CharField(
        max_length=20,
        default='OPEN',
        choices=[
            ('OPEN', 'Open'),
            ('CLOSED', 'Closed'),
        ],
        help_text="Visit status. CLOSED visits are immutable."
    )
    
    payment_type = models.CharField(
        max_length=20,
        default='CASH',
        choices=[
            ('CASH', 'Cash Payment'),
            ('INSURANCE', 'Insurance/HMO'),
        ],
        help_text="Payment type for this visit. Determines billing flow (CASH or INSURANCE)."
    )
    
    payment_status = models.CharField(
        max_length=30,
        default='UNPAID',
        choices=[
            # Standard payment flow
            ('UNPAID', 'Unpaid'),
            ('PARTIALLY_PAID', 'Partially Paid'),
            ('PAID', 'Paid'),
            # Insurance/HMO flow
            ('INSURANCE_PENDING', 'Insurance Pending'),
            ('INSURANCE_CLAIMED', 'Insurance Claimed'),
            ('SETTLED', 'Settled'),
        ],
        help_text="Payment status. Must be PAID or SETTLED for clinical actions. Insurance visits can be SETTLED with ₦0 patient payment."
    )
    
    closed_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='closed_visits',
        null=True,
        blank=True,
        help_text="Doctor who closed this visit"
    )
    
    closed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the visit was closed"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the visit was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the visit was last updated"
    )
    
    class Meta:
        db_table = 'visits'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'Visit'
        verbose_name_plural = 'Visits'
    
    def __str__(self):
        return f"Visit {self.id} - {self.patient} ({self.status})"
    
    def is_payment_cleared(self):
        """
        Check if payment is cleared.
        
        Per EMR Rules:
        - Payment is cleared if visit.payment_status is 'PAID', 'SETTLED', or 'PARTIALLY_PAID'
        - Standard flow: UNPAID → PARTIALLY_PAID → PAID
        - Insurance flow: INSURANCE_PENDING → INSURANCE_CLAIMED → SETTLED
        - Clinical actions require payment_status == 'PAID', 'SETTLED', or 'PARTIALLY_PAID'
        - Insurance visits can be SETTLED with ₦0 patient payment
        - PARTIALLY_PAID allows clinical actions to proceed (partial payment is sufficient)
        
        IMPORTANT: This method checks both bill status and visit payment_status.
        If bill status is not cleared but visit payment_status is PAID/SETTLED/PARTIALLY_PAID, 
        we trust the visit payment_status (it's the source of truth).
        """
        # First check visit payment_status (source of truth)
        # PAID, SETTLED, PARTIALLY_PAID: cleared. INSURANCE_CLAIMED: insurance approved, claim in progress.
        if self.payment_status in ['PAID', 'SETTLED', 'PARTIALLY_PAID', 'INSURANCE_CLAIMED']:
            return True
        
        # Insurance approved but visit not yet updated (e.g. approved before we synced payment_status)
        if self.payment_status == 'INSURANCE_PENDING':
            try:
                from apps.billing.insurance_models import VisitInsurance
                if VisitInsurance.objects.filter(visit_id=self.pk, approval_status='APPROVED').exists():
                    # Approved insurance => allow clinical actions; persist SETTLED so future requests pass
                    self.__class__.objects.filter(pk=self.pk).update(payment_status='SETTLED')
                    self.payment_status = 'SETTLED'
                    return True
            except Exception:
                pass
        
        # If visit payment_status is not cleared, check bill status
        # Use try-except with hasattr to avoid triggering recursive related object access
        try:
            # Check if bill_id exists before accessing bill to avoid recursion
            if hasattr(self, 'bill_id') and self.bill_id is not None:
                # Use getattr to safely access bill without triggering signals
                bill = getattr(self, 'bill', None)
                if bill:
                    # Payment is cleared if bill status is PAID, SETTLED, PARTIALLY_PAID, or INSURANCE_CLAIMED
                    if bill.status in ['PAID', 'SETTLED', 'PARTIALLY_PAID', 'INSURANCE_CLAIMED']:
                        return True
                    
                    # If there are no charges yet, it should be considered cleared for INITIAL actions
                    # (unless we explicitly add a registration/consultation fee on creation)
                    if bill.total_amount == 0:
                        return True
        except Exception:
            # If bill access fails, fall through to return False
            pass
        
        # Neither bill nor visit payment_status indicates cleared payment
        return False
    
    def compute_patient_payable(self):
        """
        Compute patient payable amount considering insurance.
        
        Returns:
            dict with:
                - total_charges: Total visit charges
                - insurance_amount: Amount covered by insurance
                - patient_payable: Amount patient must pay
                - is_fully_covered: Boolean indicating if patient pays 0
        
        Uses centralized BillingService for deterministic computation.
        """
        from apps.billing.billing_service import BillingService
        
        summary = BillingService.compute_billing_summary(self)
        
        return {
            'total_charges': summary.total_charges,
            'insurance_amount': summary.insurance_amount,
            'patient_payable': summary.patient_payable,
            'is_fully_covered': summary.is_fully_covered_by_insurance
        }
    
    def is_closed(self):
        """Check if visit is closed."""
        return self.status == 'CLOSED'
    
    def has_consultation(self):
        """Check if visit has a consultation."""
        Consultation = get_consultation_model()
        try:
            return Consultation.objects.filter(visit=self).exists()
        except Exception:
            return False
    
    def clean(self):
        """
        Validation: Ensure visit can be closed.
        
        Rules:
        1. Visit must have consultation before closure
        2. Cannot change status from CLOSED to OPEN (immutability)
        """
        # If visit is being set to CLOSED, ensure consultation exists
        if self.status == 'CLOSED' and self.pk:
            # Check if status is changing from OPEN to CLOSED
            try:
                old_visit = Visit.objects.get(pk=self.pk)
                if old_visit.status == 'OPEN':
                    # Status is changing to CLOSED, validate consultation exists
                    if not self.has_consultation():
                        raise ValidationError(
                            "Visit must have at least one consultation before it can be closed."
                        )
            except Visit.DoesNotExist:
                # New visit being created as CLOSED - not allowed
                raise ValidationError(
                    "New visits cannot be created with CLOSED status. "
                    "Visit must be OPEN initially."
                )
        
        # Prevent changing from CLOSED to OPEN
        if self.pk:
            try:
                old_visit = Visit.objects.get(pk=self.pk)
                if old_visit.status == 'CLOSED' and self.status == 'OPEN':
                    raise ValidationError(
                        "Cannot reopen a CLOSED visit. Closed visits are immutable per EMR rules."
                    )
            except Visit.DoesNotExist:
                pass
    
    def save(self, *args, **kwargs):
        """Override save to run clean() validation."""
        self.full_clean()
        super().save(*args, **kwargs)

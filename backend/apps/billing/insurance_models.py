"""
HMO/Insurance billing models - visit-scoped insurance management.

Per EMR Rules:
- All insurance data MUST be visit-scoped
- Insurance does NOT bypass billing; it alters payment responsibility
- Clinical actions still require payment_status == CLEARED
- CLEARED may mean patient payable = 0 when insurance covers full amount
- No role except Receptionist may manage insurance data
"""
from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal


class HMOProvider(models.Model):
    """
    HMO/Insurance Provider model - managed by Receptionists.
    
    Stores insurance provider information for billing purposes.
    """
    
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Name of the HMO/Insurance provider"
    )
    
    code = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        help_text="Provider code/identifier"
    )
    
    contact_person = models.CharField(
        max_length=255,
        blank=True,
        help_text="Contact person name"
    )
    
    contact_phone = models.CharField(
        max_length=50,
        blank=True,
        help_text="Contact phone number"
    )
    
    contact_email = models.EmailField(
        blank=True,
        help_text="Contact email address"
    )
    
    address = models.TextField(
        blank=True,
        help_text="Provider address"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the provider is currently active"
    )
    
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='hmo_providers_created',
        help_text="Receptionist who created this provider entry"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'hmo_providers'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
        ]
        verbose_name = 'HMO Provider'
        verbose_name_plural = 'HMO Providers'
    
    def __str__(self):
        return self.name
    
    def clean(self):
        """Validate provider data."""
        if not self.name or not self.name.strip():
            raise ValidationError("Provider name is required.")
    
    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.full_clean()
        super().save(*args, **kwargs)


class VisitInsurance(models.Model):
    """
    Visit Insurance model - visit-scoped insurance coverage.
    
    Per EMR Rules:
    - MUST be visit-scoped (ForeignKey to Visit)
    - Insurance alters payment responsibility, does NOT bypass billing
    - Clinical actions still require payment_status == CLEARED
    - CLEARED may mean patient payable = 0 when insurance covers full amount
    """
    
    COVERAGE_TYPE_CHOICES = [
        ('FULL', 'Full Coverage'),
        ('PARTIAL', 'Partial Coverage'),
    ]
    
    APPROVAL_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    
    # Core relationship - visit-scoped
    visit = models.OneToOneField(
        'visits.Visit',
        on_delete=models.CASCADE,
        related_name='insurance',
        help_text="Visit this insurance record belongs to. MUST be visit-scoped."
    )
    
    # Insurance provider
    provider = models.ForeignKey(
        'billing.HMOProvider',
        on_delete=models.PROTECT,
        related_name='visit_insurances',
        help_text="HMO/Insurance provider"
    )
    
    # Insurance details
    policy_number = models.CharField(
        max_length=100,
        help_text="Patient's insurance policy number"
    )
    
    coverage_type = models.CharField(
        max_length=20,
        choices=COVERAGE_TYPE_CHOICES,
        default='FULL',
        help_text="Type of coverage: FULL or PARTIAL"
    )
    
    # Coverage percentage (for PARTIAL coverage)
    coverage_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100.00,
        help_text="Coverage percentage (0-100). For FULL coverage, this is 100."
    )
    
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default='PENDING',
        help_text="Insurance approval status"
    )
    
    # Approval details
    approved_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Amount approved by insurance (if approved)"
    )
    
    approval_reference = models.CharField(
        max_length=255,
        blank=True,
        help_text="Insurance approval reference number"
    )
    
    approval_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date of insurance approval"
    )
    
    rejection_reason = models.TextField(
        blank=True,
        help_text="Reason for rejection (if rejected)"
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about insurance coverage"
    )
    
    # User tracking - Receptionist only
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='visit_insurances_created',
        help_text="Receptionist who created this insurance record"
    )
    
    # Audit timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'visit_insurances'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['visit']),
            models.Index(fields=['provider']),
            models.Index(fields=['approval_status']),
            models.Index(fields=['coverage_type']),
        ]
        verbose_name = 'Visit Insurance'
        verbose_name_plural = 'Visit Insurances'
    
    def __str__(self):
        return f"Insurance for Visit {self.visit_id} - {self.provider.name}"
    
    def clean(self):
        """Validate insurance data."""
        # Ensure coverage percentage is valid
        if self.coverage_percentage < 0 or self.coverage_percentage > 100:
            raise ValidationError(
                "Coverage percentage must be between 0 and 100."
            )
        
        # For FULL coverage, ensure percentage is 100
        if self.coverage_type == 'FULL' and self.coverage_percentage != 100:
            raise ValidationError(
                "FULL coverage must have coverage_percentage = 100."
            )
        
        # Validate approval status and amounts (approved_amount may be 0 for zero-claim)
        if self.approval_status == 'APPROVED':
            if self.approved_amount is None:
                raise ValidationError(
                    "Approved amount must be provided when status is APPROVED."
                )
        elif self.approval_status == 'REJECTED':
            if not self.rejection_reason:
                raise ValidationError(
                    "Rejection reason must be provided when status is REJECTED."
                )
    
    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def compute_insurance_coverage(self, total_charges):
        """
        Compute insurance-covered amount based on coverage type and approval status.
        
        Args:
            total_charges: Total visit charges (Decimal)
        
        Returns:
            dict with:
                - insurance_amount: Amount covered by insurance (Decimal)
                - patient_payable: Amount patient must pay (Decimal)
                - is_fully_covered: Boolean indicating if patient pays 0
        """
        if self.approval_status != 'APPROVED':
            # If not approved, insurance covers nothing
            return {
                'insurance_amount': Decimal('0.00'),
                'patient_payable': total_charges,
                'is_fully_covered': False
            }
        
        if self.coverage_type == 'FULL':
            # Full coverage - insurance covers all (up to approved_amount if set)
            if self.approved_amount:
                insurance_amount = min(self.approved_amount, total_charges)
            else:
                insurance_amount = total_charges
            
            patient_payable = total_charges - insurance_amount
            
            return {
                'insurance_amount': insurance_amount,
                'patient_payable': patient_payable,
                'is_fully_covered': patient_payable == 0
            }
        
        else:  # PARTIAL coverage
            # Partial coverage - insurance covers percentage
            if self.approved_amount:
                # Use approved amount if set, otherwise calculate from percentage
                insurance_amount = min(
                    self.approved_amount,
                    (total_charges * self.coverage_percentage / 100)
                )
            else:
                insurance_amount = total_charges * self.coverage_percentage / 100
            
            patient_payable = total_charges - insurance_amount
            
            return {
                'insurance_amount': insurance_amount,
                'patient_payable': patient_payable,
                'is_fully_covered': False  # Partial coverage never fully covers
            }
    
    def can_clear_payment(self, total_charges, total_payments):
        """
        Determine if visit payment can be cleared based on insurance.
        
        Per EMR Rules:
        - Payment can be CLEARED if patient_payable == 0 (insurance covers all)
        - Or if total_payments >= patient_payable
        
        Args:
            total_charges: Total visit charges (Decimal)
            total_payments: Total payments made by patient (Decimal)
        
        Returns:
            bool: True if payment can be cleared
        """
        if self.approval_status != 'APPROVED':
            # Insurance not approved - patient must pay full amount
            return total_payments >= total_charges
        
        coverage = self.compute_insurance_coverage(total_charges)
        patient_payable = coverage['patient_payable']
        
        # Payment can be cleared if:
        # 1. Patient payable is 0 (insurance covers all), OR
        # 2. Patient has paid their portion
        return patient_payable == 0 or total_payments >= patient_payable


class ClaimPolicy(models.Model):
    """Patient insurance policy (HMO/NHIA) for claims. Links patient to provider with policy details."""
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='claim_policies',
    )
    provider = models.ForeignKey(
        HMOProvider,
        on_delete=models.PROTECT,
        related_name='claim_policies',
    )
    policy_number = models.CharField(max_length=100)
    coverage_details = models.JSONField(default=dict, blank=True, help_text="Coverage limits, type, etc.")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'claim_policies'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient']),
            models.Index(fields=['provider']),
            models.Index(fields=['is_active']),
        ]
        verbose_name = 'Claim Policy'
        verbose_name_plural = 'Claim Policies'

    def __str__(self):
        return f"Policy {self.policy_number} - {self.provider.name}"


class Claim(models.Model):
    """Insurance claim (draft → submitted → approved/rejected/paid)."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
    ]
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='claims',
    )
    policy = models.ForeignKey(
        ClaimPolicy,
        on_delete=models.PROTECT,
        related_name='claims',
    )
    services = models.JSONField(
        default=list,
        help_text="List of services: consultations, labs, medications, procedures",
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    submitted_at = models.DateTimeField(null=True, blank=True)
    response_payload = models.JSONField(default=dict, blank=True, help_text="Insurer response (stub)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'insurance_claims'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient']),
            models.Index(fields=['policy']),
            models.Index(fields=['status']),
        ]
        verbose_name = 'Claim'
        verbose_name_plural = 'Claims'

    def __str__(self):
        return f"Claim {self.id} - {self.policy.provider.name} ({self.status})"

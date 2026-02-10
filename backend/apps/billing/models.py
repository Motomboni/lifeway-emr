"""
Billing models - visit-scoped payment and charge processing.

Per EMR Rules:
- Payment is visit-scoped
- Receptionist processes payments
- Payment must be CLEARED before clinical actions
- All charges belong to a Visit
- Charges are system-generated from clinical actions
- All payment actions are audited
"""
from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal

# Import bill models to ensure they're registered
from .bill_models import Bill, BillItem, BillPayment, InsuranceProvider, InsurancePolicy

# Import price list models to ensure they're registered
from .price_lists import (
    LabServicePriceList,
    PharmacyServicePriceList,
    RadiologyServicePriceList,
    ProcedureServicePriceList,
)

# Import service catalog model to ensure it's registered
from .service_catalog_models import ServiceCatalog

# Import billing line item models to ensure they're registered
from .billing_line_item_models import BillingLineItem

# Register claim models for migrations (insurance_models.InsurancePolicy, Claim)
from . import insurance_models  # noqa: F401


class Payment(models.Model):
    """
    Payment model - visit-scoped payment processing.
    
    Design Principles:
    1. ForeignKey to Visit - visit-scoped
    2. Receptionist processes payments
    3. Payment status: PENDING, CLEARED, FAILED, REFUNDED
    4. Audit timestamps for compliance
    """
    
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('POS', 'POS (Point of Sale)'),
        ('TRANSFER', 'Bank Transfer'),
        ('PAYSTACK', 'Paystack'),
        ('WALLET', 'Wallet'),
        ('INSURANCE', 'Insurance/HMO'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PARTIAL', 'Partial'),
        ('CLEARED', 'Cleared'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]
    
    # Core relationship - visit-scoped
    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.CASCADE,
        related_name='payments',
        help_text="Visit this payment belongs to. Payment is visit-scoped."
    )
    
    # Payment details
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Payment amount"
    )
    
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        help_text="Method of payment"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text="Payment status"
    )
    
    transaction_reference = models.CharField(
        max_length=255,
        blank=True,
        help_text="Transaction reference number"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Payment notes or remarks"
    )
    
    # User tracking
    processed_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='payments_processed',
        help_text="Receptionist who processed this payment. PROTECT prevents deletion."
    )
    
    # Audit timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When payment was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When payment was last updated"
    )
    
    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['visit']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_method']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
    
    def __str__(self):
        return f"Payment {self.id} - {self.amount} for Visit {self.visit_id}"
    
    def clean(self):
        """Validate payment data."""
        if self.visit_id and self.visit.status == 'CLOSED':
            raise ValidationError(
                "Cannot process payment for a CLOSED visit. Closed visits are immutable."
            )
        
        # Ensure amount is positive
        if self.amount and self.amount <= 0:
            raise ValidationError("Payment amount must be greater than zero.")
    
    def save(self, *args, **kwargs):
        """Override save to run validation and update visit payment status."""
        self.full_clean()
        super().save(*args, **kwargs)
        
        # Update visit payment status based on billing summary
        # This ensures payment status reflects the complete billing state (payments + insurance + wallet)
        if self.visit:
            from .billing_service import BillingService
            summary = BillingService.compute_billing_summary(self.visit)
            self.visit.payment_status = summary.payment_status
            self.visit.save(update_fields=['payment_status'])


class VisitCharge(models.Model):
    """
    VisitCharge model - system-generated billable events.
    
    Per EMR Rules:
    - All charges belong to a Visit (visit-scoped)
    - Charges are SYSTEM-GENERATED, not manually created
    - Doctors, nurses, labs trigger charges but don't create them directly
    - System computes totals from VisitCharge records
    - Charges cannot be modified on CLOSED visits
    
    Design Principles:
    1. ForeignKey to Visit - visit-scoped
    2. System-generated only (via signals or service methods)
    3. Charge categories match billable events from clinical actions
    4. Immutable once visit is CLOSED
    """
    
    CHARGE_CATEGORY_CHOICES = [
        ('CONSULTATION', 'Consultation'),
        ('LAB', 'Lab Order'),
        ('RADIOLOGY', 'Radiology Order'),
        ('DRUG', 'Drug Prescription'),
        ('PROCEDURE', 'Injection / Dressing'),
        ('MISC', 'Misc Services'),
    ]
    
    # Core relationship - visit-scoped
    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.CASCADE,
        related_name='charges',
        help_text="Visit this charge belongs to. All charges are visit-scoped."
    )
    
    # Charge details
    category = models.CharField(
        max_length=20,
        choices=CHARGE_CATEGORY_CHOICES,
        help_text="Charge category (system-determined from clinical action)"
    )
    
    description = models.CharField(
        max_length=255,
        help_text="Description of the charge (e.g., 'Consultation Fee', 'Lab Test: CBC')"
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Charge amount"
    )
    
    # Reference to the clinical action that triggered this charge
    # These are optional and help with audit trails
    consultation = models.ForeignKey(
        'consultations.Consultation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='charges',
        help_text="Related consultation (if charge is CONSULTATION)"
    )
    
    lab_order = models.ForeignKey(
        'laboratory.LabOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='charges',
        help_text="Related lab order (if charge is LAB)"
    )
    
    radiology_order = models.ForeignKey(
        'radiology.RadiologyOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='charges',
        help_text="Related radiology order (if charge is RADIOLOGY)"
    )
    
    prescription = models.ForeignKey(
        'pharmacy.Prescription',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='charges',
        help_text="Related prescription (if charge is DRUG)"
    )
    
    # System tracking
    created_by_system = models.BooleanField(
        default=True,
        help_text="Always True - charges are system-generated, not manually created"
    )
    
    # Audit timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When charge was created (system-generated)"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When charge was last updated"
    )
    
    class Meta:
        db_table = 'visit_charges'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['visit']),
            models.Index(fields=['category']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'Visit Charge'
        verbose_name_plural = 'Visit Charges'
    
    def __str__(self):
        return f"Charge {self.id} - {self.category} ({self.amount}) for Visit {self.visit_id}"
    
    def clean(self):
        """Validate charge data."""
        # Ensure visit is not CLOSED (charges cannot be added to closed visits)
        if self.visit_id and self.visit.status == 'CLOSED':
            raise ValidationError(
                "Cannot add charges to a CLOSED visit. Closed visits are immutable."
            )
        
        # Ensure amount is positive
        if self.amount and self.amount <= 0:
            raise ValidationError("Charge amount must be greater than zero.")
        
        # Ensure charge is system-generated (per EMR rules)
        if not self.created_by_system:
            raise ValidationError(
                "Charges must be system-generated. Manual charge creation is not allowed."
            )
    
    def save(self, *args, **kwargs):
        """Override save to run validation and update visit payment status."""
        self.full_clean()
        # Always set created_by_system to True (enforce system-generation)
        self.created_by_system = True
        super().save(*args, **kwargs)
        
        # Update visit payment status based on billing summary
        if self.visit:
            from .billing_service import BillingService
            summary = BillingService.compute_billing_summary(self.visit)
            self.visit.payment_status = summary.payment_status
            self.visit.save(update_fields=['payment_status'])
    
    @classmethod
    def create_consultation_charge(cls, visit, consultation, amount, description=None):
        """
        System method to create a consultation charge.
        
        This is called automatically when a consultation is created.
        Doctors do not call this directly - it's triggered by the system.
        """
        if visit.status == 'CLOSED':
            raise ValidationError("Cannot add charges to a CLOSED visit.")
        
        return cls.objects.create(
            visit=visit,
            category='CONSULTATION',
            description=description or f"Consultation Fee - Visit {visit.id}",
            amount=amount,
            consultation=consultation,
            created_by_system=True
        )
    
    @classmethod
    def create_lab_charge(cls, visit, lab_order, amount, description=None):
        """
        System method to create a lab order charge.
        
        This is called automatically when a lab order is created.
        Lab staff do not call this directly - it's triggered by the system.
        """
        if visit.status == 'CLOSED':
            raise ValidationError("Cannot add charges to a CLOSED visit.")
        
        return cls.objects.create(
            visit=visit,
            category='LAB',
            description=description or f"Lab Order - {lab_order.test_name if hasattr(lab_order, 'test_name') else 'Lab Test'}",
            amount=amount,
            lab_order=lab_order,
            created_by_system=True
        )
    
    @classmethod
    def create_radiology_charge(cls, visit, radiology_order, amount, description=None):
        """
        System method to create a radiology order charge.
        
        This is called automatically when a radiology order is created.
        Radiology staff do not call this directly - it's triggered by the system.
        """
        if visit.status == 'CLOSED':
            raise ValidationError("Cannot add charges to a CLOSED visit.")
        
        return cls.objects.create(
            visit=visit,
            category='RADIOLOGY',
            description=description or f"Radiology Order - {radiology_order.study_type if hasattr(radiology_order, 'study_type') else 'Radiology Study'}",
            amount=amount,
            radiology_order=radiology_order,
            created_by_system=True
        )
    
    @classmethod
    def create_drug_charge(cls, visit, prescription, amount, description=None):
        """
        System method to create a drug prescription charge.
        
        This is called automatically when a prescription is created.
        Doctors/pharmacy do not call this directly - it's triggered by the system.
        """
        if visit.status == 'CLOSED':
            raise ValidationError("Cannot add charges to a CLOSED visit.")
        
        return cls.objects.create(
            visit=visit,
            category='DRUG',
            description=description or f"Drug Prescription - {prescription.medication_name if hasattr(prescription, 'medication_name') else 'Medication'}",
            amount=amount,
            prescription=prescription,
            created_by_system=True
        )
    
    @classmethod
    def create_procedure_charge(cls, visit, amount, description):
        """
        System method to create a procedure charge (injection, dressing, etc.).
        
        This is called automatically when a procedure is performed.
        Nurses/doctors do not call this directly - it's triggered by the system.
        """
        if visit.status == 'CLOSED':
            raise ValidationError("Cannot add charges to a CLOSED visit.")
        
        return cls.objects.create(
            visit=visit,
            category='PROCEDURE',
            description=description,
            amount=amount,
            created_by_system=True
        )
    
    @classmethod
    def create_misc_charge(cls, visit, amount, description):
        """
        System method to create a miscellaneous service charge.
        
        This is called automatically when a misc service is provided.
        Staff do not call this directly - it's triggered by the system.
        """
        if visit.status == 'CLOSED':
            raise ValidationError("Cannot add charges to a CLOSED visit.")
        
        return cls.objects.create(
            visit=visit,
            category='MISC',
            description=description,
            amount=amount,
            created_by_system=True
        )
    
    @classmethod
    def get_total_charges_for_visit(cls, visit):
        """
        Calculate total charges for a visit.
        
        This is used by the Visit model to compute patient payable amounts.
        """
        return cls.objects.filter(visit=visit).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')


class PaymentIntent(models.Model):
    """
    PaymentIntent model - Paystack transaction tracking for Visit billing.
    
    Per EMR Rules:
    - PaymentIntent is visit-scoped (maps to Visit)
    - Paystack reference maps to a Visit
    - No PHI is sent to Paystack (only visit_id in metadata)
    - Verification occurs server-side only
    - Payment records are immutable once verified
    
    Design Principles:
    1. ForeignKey to Visit - visit-scoped
    2. Tracks Paystack transaction lifecycle
    3. Prevents duplicate processing (idempotency)
    4. Immutable after verification
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('INITIALIZED', 'Initialized'),
        ('VERIFIED', 'Verified'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    # Core relationship - visit-scoped
    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.CASCADE,
        related_name='payment_intents',
        help_text="Visit this payment intent belongs to. PaymentIntent is visit-scoped."
    )
    
    # Paystack transaction details
    paystack_reference = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Paystack transaction reference (unique identifier)"
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Payment amount (in NGN)"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text="Payment intent status"
    )
    
    # Paystack response data (stored for audit)
    paystack_authorization_url = models.URLField(
        blank=True,
        null=True,
        help_text="Paystack authorization URL (from initialization)"
    )
    
    paystack_access_code = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Paystack access code (from initialization)"
    )
    
    # Verification data (from Paystack webhook/verification)
    paystack_transaction_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Paystack transaction ID (from verification)"
    )
    
    paystack_customer_email = models.EmailField(
        blank=True,
        null=True,
        help_text="Customer email from Paystack (not PHI - generic payment email)"
    )
    
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When payment was verified (server-side)"
    )
    
    # Related Payment record (created after verification)
    payment = models.OneToOneField(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payment_intent',
        help_text="Payment record created after verification (immutable once set)"
    )
    
    # User tracking
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='payment_intents_created',
        help_text="Receptionist who created this payment intent"
    )
    
    # Audit timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When payment intent was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When payment intent was last updated"
    )
    
    class Meta:
        db_table = 'payment_intents'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['visit']),
            models.Index(fields=['paystack_reference']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'Payment Intent'
        verbose_name_plural = 'Payment Intents'
    
    def __str__(self):
        return f"PaymentIntent {self.id} - {self.paystack_reference} for Visit {self.visit_id}"
    
    def clean(self):
        """Validate payment intent data."""
        # Ensure visit is not CLOSED
        if self.visit_id and self.visit.status == 'CLOSED':
            raise ValidationError(
                "Cannot create payment intent for a CLOSED visit. Closed visits are immutable."
            )
        
        # Ensure amount is positive
        if self.amount and self.amount <= 0:
            raise ValidationError("Payment amount must be greater than zero.")
        
        # Ensure paystack_reference is unique (enforced at DB level, but validate here too)
        if self.paystack_reference:
            existing = PaymentIntent.objects.filter(
                paystack_reference=self.paystack_reference
            ).exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError(
                    f"Payment intent with reference {self.paystack_reference} already exists."
                )
    
    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def is_verified(self):
        """Check if payment intent is verified."""
        return self.status == 'VERIFIED' and self.payment is not None
    
    def can_be_modified(self):
        """Check if payment intent can be modified (not verified)."""
        return self.status not in ['VERIFIED', 'CANCELLED']
    
    def mark_as_verified(self, paystack_data: dict):
        """
        Mark payment intent as verified and create Payment record.
        
        This is called server-side only after Paystack verification.
        Payment record is immutable once created.
        
        Args:
            paystack_data: Paystack transaction verification response
        """
        if self.status == 'VERIFIED':
            # Already verified - idempotency check
            return self.payment
        
        if not self.can_be_modified():
            raise ValidationError(
                f"Cannot verify payment intent in status {self.status}"
            )
        
        from django.utils import timezone
        
        # Update status
        self.status = 'VERIFIED'
        self.verified_at = timezone.now()
        
        # Store Paystack transaction details
        if 'data' in paystack_data:
            data = paystack_data['data']
            self.paystack_transaction_id = data.get('id', '')
            if 'customer' in data:
                self.paystack_customer_email = data['customer'].get('email', '')
        
        self.save()
        
        # Create Payment record (immutable once created)
        if not self.payment:
            self.payment = Payment.objects.create(
                visit=self.visit,
                amount=self.amount,
                payment_method='PAYSTACK',
                status='CLEARED',  # Paystack verified = cleared
                transaction_reference=self.paystack_reference,
                notes=f"Paystack payment verified. Transaction ID: {self.paystack_transaction_id}",
                processed_by=self.created_by
            )
            self.save(update_fields=['payment'])
        
        return self.payment
    
    def mark_as_failed(self, reason: str = None):
        """Mark payment intent as failed."""
        if not self.can_be_modified():
            raise ValidationError(
                f"Cannot mark payment intent as failed in status {self.status}"
            )
        
        self.status = 'FAILED'
        if reason:
            # Store failure reason in notes if we had a notes field
            pass
        self.save()

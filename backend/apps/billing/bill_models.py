"""
Bill and BillItem models for visit-scoped billing system.

Per EMR Rules:
- Bill is OneToOne with Visit
- BillItem belongs to Bill
- Payment belongs to Bill
- Bill auto-calculates totals
- Insurance bills have special rules
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.db.models import Q
from django.utils import timezone
from decimal import Decimal


class Bill(models.Model):
    """
    Bill model - OneToOne with Visit.
    
    Per EMR Rules:
    - One bill per visit
    - Bill auto-calculates totals
    - Insurance bills cannot accept Paystack/Cash
    - Insurance bills generate invoices, not receipts
    """
    
    # OneToOne relationship with Visit
    # CASCADE ensures no Bill without Visit (database constraint)
    visit = models.OneToOneField(
        'visits.Visit',
        on_delete=models.CASCADE,
        related_name='bill',
        help_text="Visit this bill belongs to. One bill per visit.",
        db_constraint=True  # Explicit database constraint
    )
    
    # Insurance flag
    is_insurance_backed = models.BooleanField(
        default=False,
        help_text="Whether this bill is backed by insurance. Insurance bills cannot accept Paystack/Cash."
    )
    
    # Auto-calculated fields (cached for performance)
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total bill amount (sum of all bill items)"
    )
    
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total amount paid (sum of all payments)"
    )
    
    outstanding_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Outstanding balance (total_amount - amount_paid)"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=[
            ('UNPAID', 'Unpaid'),
            ('PARTIALLY_PAID', 'Partially Paid'),
            ('PAID', 'Paid'),
            ('INSURANCE_PENDING', 'Insurance Pending'),
            ('INSURANCE_CLAIMED', 'Insurance Claimed'),
            ('SETTLED', 'Settled'),
        ],
        default='UNPAID',
        help_text="Bill payment status"
    )
    
    # Insurance policy reference (if insurance-backed)
    insurance_policy = models.ForeignKey(
        'billing.InsurancePolicy',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bills',
        help_text="Insurance policy for this bill (if insurance-backed)"
    )
    
    # Audit fields
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bills_created',
        help_text="User who created this bill"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When bill was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When bill was last updated"
    )
    
    class Meta:
        db_table = 'bills'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['visit']),
            models.Index(fields=['status']),
            models.Index(fields=['is_insurance_backed']),
            models.Index(fields=['created_at']),
            models.Index(fields=['created_by']),
        ]
        constraints = [
            # Ensure no Bill without Visit (OneToOne already enforces this, but explicit constraint)
            models.CheckConstraint(
                condition=Q(visit__isnull=False),
                name='bill_requires_visit'
            ),
        ]
        verbose_name = 'Bill'
        verbose_name_plural = 'Bills'
    
    def __str__(self):
        return f"Bill {self.id} - Visit {self.visit_id} - {self.total_amount} NGN"
    
    def clean(self):
        """Validate bill data."""
        # If insurance-backed, insurance_policy must be set
        if self.is_insurance_backed and not self.insurance_policy:
            raise ValidationError(
                "Insurance-backed bills must have an insurance policy."
            )
        
        # If not insurance-backed, insurance_policy should not be set
        if not self.is_insurance_backed and self.insurance_policy:
            raise ValidationError(
                "Non-insurance bills cannot have an insurance policy."
            )
    
    def save(self, *args, **kwargs):
        """Override save to run validation and recalculate totals."""
        self.full_clean()
        
        # Recalculate totals before saving, but only if instance already exists
        # (related managers like self.items require a primary key)
        if self.pk:
            self.recalculate_totals()
        
        super().save(*args, **kwargs)
    
    def add_item(self, department: str, service_name: str, amount: Decimal, created_by=None, item_status=None):
        """
        Add a bill item to this bill.
        
        Args:
            department: Department name (e.g., 'LAB', 'PHARMACY', 'RADIOLOGY')
            service_name: Name of the service/item
            amount: Item amount (must be > 0)
            created_by: User who created the item (for audit)
            item_status: Item status (UNPAID, PAID, INSURANCE). Defaults to UNPAID or INSURANCE based on bill type.
        
        Returns:
            BillItem: Created bill item
        """
        if amount <= 0:
            raise ValidationError("Bill item amount must be greater than zero.")
        
        if self.visit.status == 'CLOSED':
            raise ValidationError("Cannot add items to a bill for a CLOSED visit.")
        
        # Determine item status
        if item_status is None:
            # Auto-set status based on bill type
            if self.is_insurance_backed:
                item_status = 'INSURANCE'
            else:
                item_status = 'UNPAID'
        
        bill_item = BillItem.objects.create(
            bill=self,
            department=department,
            service_name=service_name,
            amount=amount,
            status=item_status,
            created_by=created_by
        )
        
        # Create corresponding VisitCharge for backward compatibility with legacy system
        # This ensures charges show up in the charges endpoint
        # Use lazy import to avoid circular import issues
        try:
            # Import here to avoid circular import (models.py imports bill_models.py)
            from apps.billing.models import VisitCharge
            
            # Map department to VisitCharge category
            category_mapping = {
                'LAB': 'LAB',
                'PHARMACY': 'DRUG',
                'RADIOLOGY': 'RADIOLOGY',
                'PROCEDURE': 'PROCEDURE',
                'CONSULTATION': 'CONSULTATION',
            }
            
            charge_category = category_mapping.get(department, 'MISC')
            
            # Create VisitCharge (system-generated for backward compatibility)
            # Check if a similar charge already exists to avoid duplicates
            existing_charge = VisitCharge.objects.filter(
                visit=self.visit,
                category=charge_category,
                description=service_name,
                amount=amount
            ).first()
            
            if not existing_charge:
                VisitCharge.objects.create(
                    visit=self.visit,
                    category=charge_category,
                    description=service_name,
                    amount=amount,
                    created_by_system=True
                )
        except Exception as e:
            # Log error but don't fail bill item creation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(
                f"Failed to create VisitCharge for BillItem {bill_item.id}: {str(e)}",
                exc_info=True
            )
        
        # Recalculate totals
        self.recalculate_totals()
        self.save(update_fields=['total_amount', 'outstanding_balance', 'updated_at'])
        
        return bill_item
    
    def add_payment(self, amount: Decimal, payment_method: str, transaction_reference: str = '', 
                   notes: str = '', processed_by=None):
        """
        Add a payment to this bill.
        
        Per EMR Rules:
        - Insurance bills cannot accept Paystack/Cash
        - Payments are append-only (no delete)
        
        Args:
            amount: Payment amount (must be > 0)
            payment_method: Payment method (CASH, POS, TRANSFER, PAYSTACK, WALLET, INSURANCE)
            transaction_reference: Transaction reference number
            notes: Payment notes
            processed_by: Receptionist who processed the payment
        
        Returns:
            Payment: Created payment record
        """
        if amount <= 0:
            raise ValidationError("Payment amount must be greater than zero.")
        
        if self.visit.status == 'CLOSED':
            raise ValidationError("Cannot add payments to a bill for a CLOSED visit.")
        
        # Insurance bills cannot accept Paystack/Cash
        if self.is_insurance_backed and payment_method in ['PAYSTACK', 'CASH']:
            raise ValidationError(
                f"Insurance-backed bills cannot accept {payment_method} payments. "
                "Only POS, TRANSFER, WALLET, or INSURANCE methods are allowed."
            )
        
        # Create payment
        payment = BillPayment.objects.create(
            bill=self,
            amount=amount,
            payment_method=payment_method,
            transaction_reference=transaction_reference,
            notes=notes,
            processed_by=processed_by
        )
        
        # Recalculate totals
        self.recalculate_totals()
        self.save(update_fields=['amount_paid', 'outstanding_balance', 'status', 'updated_at'])
        
        return payment
    
    def recalculate_totals(self):
        """
        Recalculate bill totals.
        
        Calculates:
        - total_amount: Sum of all bill items
        - amount_paid: Sum of all payments
        - outstanding_balance: total_amount - amount_paid
        - status: Based on outstanding_balance and insurance status
        """
        # Calculate total amount from bill items
        total_items = self.items.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        self.total_amount = total_items
        
        # Calculate amount paid from payments
        total_payments = self.payments.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        self.amount_paid = total_payments
        
        # Calculate outstanding balance
        self.outstanding_balance = self.total_amount - self.amount_paid
        
        # Update status based on outstanding balance and insurance
        if self.is_insurance_backed:
            if self.outstanding_balance <= 0:
                self.status = 'SETTLED'
            elif self.amount_paid > 0:
                self.status = 'INSURANCE_CLAIMED'
            else:
                self.status = 'INSURANCE_PENDING'
        else:
            if self.outstanding_balance <= 0:
                self.status = 'PAID'
            elif self.amount_paid > 0:
                self.status = 'PARTIALLY_PAID'
            else:
                self.status = 'UNPAID'
    
    def can_generate_receipt(self):
        """Check if bill can generate a receipt (non-insurance bills)."""
        return not self.is_insurance_backed
    
    def can_generate_invoice(self):
        """Check if bill can generate an invoice (insurance bills)."""
        return self.is_insurance_backed


class BillItem(models.Model):
    """
    BillItem model - belongs to Bill.
    
    Represents individual line items on a bill.
    """
    
    DEPARTMENT_CHOICES = [
        ('CONSULTATION', 'Consultation'),
        ('LAB', 'Laboratory'),
        ('RADIOLOGY', 'Radiology'),
        ('PHARMACY', 'Pharmacy'),
        ('PROCEDURE', 'Procedure'),
        ('MISC', 'Miscellaneous'),
    ]
    
    STATUS_CHOICES = [
        ('UNPAID', 'Unpaid'),
        ('PAID', 'Paid'),
        ('INSURANCE', 'Insurance'),
    ]
    
    # ForeignKey to Bill
    # CASCADE ensures no orphan BillItems (database constraint)
    bill = models.ForeignKey(
        Bill,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="Bill this item belongs to",
        db_constraint=True  # Explicit database constraint
    )
    
    # Item details
    department = models.CharField(
        max_length=50,
        choices=DEPARTMENT_CHOICES,
        help_text="Department that provided this service"
    )
    
    service_name = models.CharField(
        max_length=255,
        help_text="Name of the service/item"
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Item amount"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='UNPAID',
        help_text="Item payment status"
    )
    
    # Audit fields
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bill_items_created',
        help_text="User who created this item"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When item was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When item was last updated"
    )
    
    class Meta:
        db_table = 'bill_items'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['bill']),
            models.Index(fields=['department']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['created_by']),
        ]
        constraints = [
            # Ensure no orphan BillItems (ForeignKey CASCADE already enforces this, but explicit constraint)
            models.CheckConstraint(
                condition=Q(bill__isnull=False),
                name='bill_item_requires_bill'
            ),
        ]
        verbose_name = 'Bill Item'
        verbose_name_plural = 'Bill Items'
    
    def __str__(self):
        return f"{self.service_name} - {self.amount} NGN ({self.department})"
    
    def clean(self):
        """Validate bill item data."""
        if self.amount <= 0:
            raise ValidationError("Bill item amount must be greater than zero.")
        
        if self.bill and self.bill.visit.status == 'CLOSED':
            raise ValidationError("Cannot modify items for a bill on a CLOSED visit.")
    
    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.full_clean()
        super().save(*args, **kwargs)
        
        # Recalculate bill totals
        if self.bill:
            self.bill.recalculate_totals()
            self.bill.save(update_fields=['total_amount', 'outstanding_balance', 'updated_at'])
    
    def delete(self, *args, **kwargs):
        """Prevent deletion - bill items are immutable."""
        raise ValidationError("Bill items are immutable and cannot be deleted.")


class BillPayment(models.Model):
    """
    BillPayment model - belongs to Bill.
    
    Per EMR Rules:
    - Payments are append-only (no delete)
    - Payments belong to a Bill (not directly to Visit)
    """
    
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('POS', 'POS (Point of Sale)'),
        ('TRANSFER', 'Bank Transfer'),
        ('PAYSTACK', 'Paystack'),
        ('WALLET', 'Wallet'),
        ('INSURANCE', 'Insurance/HMO'),
    ]
    
    # ForeignKey to Bill
    # CASCADE ensures no payment without Bill (database constraint)
    bill = models.ForeignKey(
        Bill,
        on_delete=models.CASCADE,
        related_name='payments',
        help_text="Bill this payment belongs to",
        db_constraint=True  # Explicit database constraint
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
    # PROTECT ensures user cannot be deleted if they processed payments
    processed_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='bill_payments_processed',
        help_text="Receptionist who processed this payment",
        db_constraint=True  # Explicit database constraint
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
        db_table = 'bill_payments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['bill']),
            models.Index(fields=['payment_method']),
            models.Index(fields=['created_at']),
            models.Index(fields=['processed_by']),
        ]
        constraints = [
            # Ensure no payment without Bill (ForeignKey CASCADE already enforces this, but explicit constraint)
            models.CheckConstraint(
                condition=Q(bill__isnull=False),
                name='bill_payment_requires_bill'
            ),
            # Ensure processed_by is set (PROTECT already enforces this, but explicit constraint)
            models.CheckConstraint(
                condition=Q(processed_by__isnull=False),
                name='bill_payment_requires_processor'
            ),
        ]
        verbose_name = 'Bill Payment'
        verbose_name_plural = 'Bill Payments'
    
    class Meta:
        # Use a different table name to avoid conflicts
        db_table = 'bill_payments'
    
    def __str__(self):
        return f"Payment {self.id} - {self.amount} NGN for Bill {self.bill_id}"
    
    def clean(self):
        """Validate payment data."""
        if self.amount <= 0:
            raise ValidationError("Payment amount must be greater than zero.")
        
        if self.bill and self.bill.visit.status == 'CLOSED':
            raise ValidationError(
                "Cannot add payments to a bill for a CLOSED visit. Closed visits are immutable."
            )
    
    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.full_clean()
        super().save(*args, **kwargs)
        
        # Recalculate bill totals
        if self.bill:
            self.bill.recalculate_totals()
            self.bill.save(update_fields=['amount_paid', 'outstanding_balance', 'status', 'updated_at'])
    
    def delete(self, *args, **kwargs):
        """Prevent deletion - payments are append-only."""
        raise ValidationError("Payments are append-only and cannot be deleted.")


class InsuranceProvider(models.Model):
    """
    Insurance Provider model.
    
    Stores insurance provider information.
    """
    
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Name of the insurance provider"
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
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When provider was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When provider was last updated"
    )
    
    class Meta:
        db_table = 'insurance_providers'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
        ]
        verbose_name = 'Insurance Provider'
        verbose_name_plural = 'Insurance Providers'
    
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


class InsurancePolicy(models.Model):
    """
    Insurance Policy model.
    
    Represents an insurance policy for a patient.
    """
    
    # Patient reference
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='insurance_policies',
        help_text="Patient this policy belongs to"
    )
    
    # Provider reference
    provider = models.ForeignKey(
        InsuranceProvider,
        on_delete=models.PROTECT,
        related_name='policies',
        help_text="Insurance provider"
    )
    
    # Policy details
    policy_number = models.CharField(
        max_length=255,
        help_text="Insurance policy number"
    )
    
    coverage_type = models.CharField(
        max_length=50,
        choices=[
            ('FULL', 'Full Coverage'),
            ('PARTIAL', 'Partial Coverage'),
        ],
        default='FULL',
        help_text="Type of coverage"
    )
    
    coverage_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('100.00'),
        help_text="Coverage percentage (0-100)"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the policy is currently active"
    )
    
    valid_from = models.DateField(
        help_text="Policy validity start date"
    )
    
    valid_to = models.DateField(
        null=True,
        blank=True,
        help_text="Policy validity end date (if applicable)"
    )
    
    # Audit fields
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When policy was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When policy was last updated"
    )
    
    class Meta:
        db_table = 'insurance_policies'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient']),
            models.Index(fields=['provider']),
            models.Index(fields=['policy_number']),
            models.Index(fields=['is_active']),
        ]
        verbose_name = 'Insurance Policy'
        verbose_name_plural = 'Insurance Policies'
    
    def __str__(self):
        return f"{self.provider.name} - {self.policy_number} ({self.patient.get_full_name()})"
    
    def clean(self):
        """Validate policy data."""
        if not self.policy_number or not self.policy_number.strip():
            raise ValidationError("Policy number is required.")
        
        if self.coverage_percentage < 0 or self.coverage_percentage > 100:
            raise ValidationError("Coverage percentage must be between 0 and 100.")
        
        if self.valid_to and self.valid_to < self.valid_from:
            raise ValidationError("Policy end date must be after start date.")
    
    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def is_valid(self):
        """Check if policy is currently valid."""
        if not self.is_active:
            return False
        
        today = timezone.now().date()
        if today < self.valid_from:
            return False
        
        if self.valid_to and today > self.valid_to:
            return False
        
        return True


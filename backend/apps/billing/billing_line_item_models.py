"""
BillingLineItem models - ServiceCatalog-driven billing system.

Per EMR Rules:
- Every billable service creates exactly one BillingLineItem
- BillingLineItem is generated from ServiceCatalog
- Amount is snapshotted at time of billing
- Billing is immutable once paid
- No orphan bills allowed
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q
from decimal import Decimal


class BillingLineItem(models.Model):
    """
    BillingLineItem model - ServiceCatalog-driven billing.
    
    Every billable service creates exactly one BillingLineItem.
    The amount is snapshotted at the time of billing to preserve
    historical pricing even if ServiceCatalog prices change.
    
    Design Principles:
    1. ForeignKey to ServiceCatalog - links to service definition
    2. ForeignKey to Visit - visit-scoped billing
    3. Optional ForeignKey to Consultation - for consultation services
    4. Amount is snapshotted (not computed from ServiceCatalog)
    5. Immutable once paid (bill_status = PAID)
    6. No orphan bills (CASCADE ensures visit/service_catalog deletion removes line items)
    """
    
    BILL_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PARTIALLY_PAID', 'Partially Paid'),
        ('PAID', 'Paid'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('WALLET', 'Wallet'),
        ('HMO', 'HMO/Insurance'),
        ('PAYSTACK', 'Paystack'),
    ]
    
    # Core relationships
    service_catalog = models.ForeignKey(
        'billing.ServiceCatalog',
        on_delete=models.CASCADE,
        related_name='billing_line_items',
        help_text="ServiceCatalog service that generated this billing line item",
        db_constraint=True
    )
    
    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.CASCADE,
        related_name='billing_line_items',
        help_text="Visit this billing line item belongs to",
        db_constraint=True
    )
    
    consultation = models.ForeignKey(
        'consultations.Consultation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='billing_line_items',
        help_text="Consultation this billing line item is associated with (optional, for consultation services)",
        db_constraint=True
    )
    
    # Snapshot fields (preserve historical pricing)
    source_service_code = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Service code at time of billing (snapshot from ServiceCatalog.service_code)"
    )
    
    source_service_name = models.CharField(
        max_length=255,
        help_text="Service name at time of billing (snapshot from ServiceCatalog.name)"
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Billing amount (snapshot from ServiceCatalog.amount at time of billing)"
    )
    
    # Payment tracking
    bill_status = models.CharField(
        max_length=20,
        choices=BILL_STATUS_CHOICES,
        default='PENDING',
        db_index=True,
        help_text="Payment status of this billing line item"
    )
    
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Amount paid against this line item"
    )
    
    outstanding_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Outstanding amount (amount - amount_paid)"
    )
    
    # Payment method (for tracking how this item was paid)
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        blank=True,
        null=True,
        help_text="Payment method used (if paid)"
    )
    
    # Audit fields (Per EMR Context Document v2: Every entity must track created_by, created_at, modified_by, modified_at)
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='billing_line_items_created',
        help_text="User who created this billing line item"
    )
    
    modified_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='billing_line_items_modified',
        help_text="User who last modified this billing line item"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this billing line item was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this billing line item was last updated (modified_at equivalent)"
    )
    
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this billing line item was fully paid"
    )
    
    class Meta:
        db_table = 'billing_line_items'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['service_catalog']),
            models.Index(fields=['visit']),
            models.Index(fields=['consultation']),
            models.Index(fields=['source_service_code']),
            models.Index(fields=['bill_status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['visit', 'bill_status']),
            models.Index(fields=['service_catalog', 'visit']),
        ]
        constraints = [
            # Ensure no orphan line items
            models.CheckConstraint(
                condition=Q(service_catalog__isnull=False) & Q(visit__isnull=False),
                name='billing_line_item_requires_service_and_visit'
            ),
            # Ensure amount is positive
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name='billing_line_item_amount_positive'
            ),
            # Ensure outstanding_amount is non-negative
            models.CheckConstraint(
                condition=Q(outstanding_amount__gte=0),
                name='billing_line_item_outstanding_non_negative'
            ),
            # Ensure amount_paid <= amount
            models.CheckConstraint(
                condition=Q(amount_paid__lte=models.F('amount')),
                name='billing_line_item_paid_not_exceed_amount'
            ),
        ]
        verbose_name = 'Billing Line Item'
        verbose_name_plural = 'Billing Line Items'
    
    def __str__(self):
        return f"{self.source_service_code} - {self.amount} NGN ({self.bill_status})"
    
    def clean(self):
        """Validate billing line item data."""
        errors = {}
        
        # Validate amount
        if self.amount <= 0:
            errors['amount'] = "Billing amount must be greater than zero."
        
        # Validate outstanding_amount
        if self.outstanding_amount < 0:
            errors['outstanding_amount'] = "Outstanding amount cannot be negative."
        
        # Validate amount_paid
        if self.amount_paid < 0:
            errors['amount_paid'] = "Amount paid cannot be negative."
        
        if self.amount_paid > self.amount:
            errors['amount_paid'] = "Amount paid cannot exceed billing amount."
        
        # Validate outstanding_amount calculation
        expected_outstanding = self.amount - self.amount_paid
        if self.outstanding_amount != expected_outstanding:
            errors['outstanding_amount'] = (
                f"Outstanding amount must equal (amount - amount_paid). "
                f"Expected: {expected_outstanding}, Got: {self.outstanding_amount}"
            )
        
        # Validate consultation relationship
        if self.consultation:
            # Consultation must belong to the same visit
            if self.consultation.visit != self.visit:
                errors['consultation'] = (
                    "Consultation must belong to the same visit as the billing line item."
                )
            
            # Service must be a consultation service
            if self.service_catalog.workflow_type != 'GOPD_CONSULT':
                errors['consultation'] = (
                    "Consultation can only be linked to GOPD_CONSULT services."
                )
        
        # ❌ GOVERNANCE RULE: Billing is immutable once paid
        # Per EMR Context Document v2: "Billing is immutable once paid"
        # Only enforce when the item was ALREADY PAID in DB (not when transitioning PENDING -> PAID)
        if self.pk:
            try:
                old_instance = BillingLineItem.objects.get(pk=self.pk)
                if old_instance.bill_status != 'PAID':
                    old_instance = None  # Skip immutability checks
            except BillingLineItem.DoesNotExist:
                old_instance = None
        else:
            old_instance = None
        if self.pk and old_instance and old_instance.bill_status == 'PAID':
            # Item was already PAID in DB - enforce immutability
            if old_instance.amount != self.amount:
                errors['amount'] = (
                    "Cannot modify amount for a PAID billing line item. "
                    "Per EMR governance rules, billing is immutable once paid."
                )
            if old_instance.service_catalog_id != self.service_catalog_id:
                errors['service_catalog'] = (
                    "Cannot modify service_catalog for a PAID billing line item. "
                    "Per EMR governance rules, billing is immutable once paid."
                )
            if old_instance.visit_id != self.visit_id:
                errors['visit'] = (
                    "Cannot modify visit for a PAID billing line item. "
                    "Per EMR governance rules, billing is immutable once paid."
                )
            if old_instance.consultation_id != self.consultation_id:
                errors['consultation'] = (
                    "Cannot modify consultation for a PAID billing line item. "
                    "Per EMR governance rules, billing is immutable once paid."
                )
            if old_instance.payment_method != self.payment_method:
                errors['payment_method'] = (
                    "Cannot modify payment_method for a PAID billing line item. "
                    "Per EMR governance rules, billing is immutable once paid."
                )
        
        # Validate visit status
        if self.visit and self.visit.status == 'CLOSED':
            if self.bill_status != 'PAID':
                errors['visit'] = (
                    "Cannot create or modify unpaid billing line items for a CLOSED visit."
                )
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """
        Override save to run validation and calculate outstanding_amount.
        
        Per EMR Context Document v2:
        - Billing is immutable once paid
        - Every action must be auditable (track modified_by)
        """
        # Track who is modifying (for audit)
        # Note: modified_by should be set by the view/serializer before calling save()
        if 'modified_by' in kwargs:
            self.modified_by = kwargs.pop('modified_by')
        elif hasattr(self, '_modified_by'):
            self.modified_by = self._modified_by
        
        # Always calculate outstanding_amount
        self.outstanding_amount = self.amount - self.amount_paid
        
        # Snapshot service details if not set
        if not self.source_service_code:
            self.source_service_code = self.service_catalog.service_code
        if not self.source_service_name:
            self.source_service_name = self.service_catalog.name
        
        # Update bill_status based on payment
        if self.amount_paid >= self.amount:
            self.bill_status = 'PAID'
            if not self.paid_at:
                from django.utils import timezone
                self.paid_at = timezone.now()
        elif self.amount_paid > 0:
            self.bill_status = 'PARTIALLY_PAID'
        else:
            self.bill_status = 'PENDING'
        
        # Run validation (includes immutability check for PAID items)
        self.full_clean()
        super().save(*args, **kwargs)
    
    def apply_payment(self, payment_amount: Decimal, payment_method: str) -> None:
        """
        Apply payment to this billing line item.
        
        Args:
            payment_amount: Amount to apply
            payment_method: Payment method (CASH, WALLET, HMO, PAYSTACK)
        
        Raises:
            ValidationError: If item is already paid or payment exceeds outstanding amount
        """
        if self.bill_status == 'PAID':
            raise ValidationError("Cannot apply payment to a fully paid billing line item.")
        
        if payment_amount <= 0:
            raise ValidationError("Payment amount must be greater than zero.")
        
        if payment_amount > self.outstanding_amount:
            raise ValidationError(
                f"Payment amount ({payment_amount}) exceeds outstanding amount ({self.outstanding_amount})."
            )
        
        # Update payment tracking
        self.amount_paid += payment_amount
        self.outstanding_amount = self.amount - self.amount_paid
        self.payment_method = payment_method
        
        # Update status
        if self.amount_paid >= self.amount:
            self.bill_status = 'PAID'
            from django.utils import timezone
            self.paid_at = timezone.now()
        else:
            self.bill_status = 'PARTIALLY_PAID'
        
        self.save()
    
    def is_immutable(self) -> bool:
        """Check if this billing line item is immutable (paid)."""
        return self.bill_status == 'PAID'
    
    def can_be_modified(self) -> bool:
        """Check if this billing line item can be modified."""
        return not self.is_immutable() and self.visit.status == 'OPEN'
    
    def delete(self, *args, **kwargs):
        """Prevent deletion of paid items."""
        if self.is_immutable():
            raise ValidationError(
                "Cannot delete a PAID billing line item. Paid items are immutable."
            )
        super().delete(*args, **kwargs)


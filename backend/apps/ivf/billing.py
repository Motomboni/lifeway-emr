"""
IVF Billing Integration

Handles billing for IVF services including:
- Cycle packages
- Individual procedures (retrieval, transfer, etc.)
- Medications
- Laboratory services (sperm analysis, embryology)
- Cryopreservation storage fees

Nigerian Healthcare Billing:
- Supports Naira (NGN) currency
- Insurance pre-authorization tracking
- Payment plan support for expensive cycles
"""
from decimal import Decimal
from django.db import models
from django.utils import timezone

from apps.billing.models import VisitCharge


class IVFServiceCategory:
    """IVF service categories for billing."""
    CYCLE_PACKAGE = 'IVF_CYCLE_PACKAGE'
    CONSULTATION = 'IVF_CONSULTATION'
    STIMULATION = 'IVF_STIMULATION'
    RETRIEVAL = 'IVF_RETRIEVAL'
    FERTILIZATION = 'IVF_FERTILIZATION'
    EMBRYO_CULTURE = 'IVF_EMBRYO_CULTURE'
    TRANSFER = 'IVF_TRANSFER'
    CRYOPRESERVATION = 'IVF_CRYOPRESERVATION'
    SPERM_ANALYSIS = 'IVF_SPERM_ANALYSIS'
    PGT = 'IVF_PGT'
    MEDICATION = 'IVF_MEDICATION'
    STORAGE = 'IVF_STORAGE'


class IVFPriceList(models.Model):
    """
    IVF Service Price List
    
    Maintains pricing for all IVF-related services.
    Supports tiered pricing and package deals.
    """
    
    CATEGORY_CHOICES = [
        (IVFServiceCategory.CYCLE_PACKAGE, 'IVF Cycle Package'),
        (IVFServiceCategory.CONSULTATION, 'IVF Consultation'),
        (IVFServiceCategory.STIMULATION, 'Ovarian Stimulation'),
        (IVFServiceCategory.RETRIEVAL, 'Oocyte Retrieval'),
        (IVFServiceCategory.FERTILIZATION, 'Fertilization/ICSI'),
        (IVFServiceCategory.EMBRYO_CULTURE, 'Embryo Culture'),
        (IVFServiceCategory.TRANSFER, 'Embryo Transfer'),
        (IVFServiceCategory.CRYOPRESERVATION, 'Cryopreservation'),
        (IVFServiceCategory.SPERM_ANALYSIS, 'Sperm Analysis'),
        (IVFServiceCategory.PGT, 'Genetic Testing'),
        (IVFServiceCategory.MEDICATION, 'Medication'),
        (IVFServiceCategory.STORAGE, 'Storage Fee'),
    ]
    
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Service code"
    )
    
    name = models.CharField(
        max_length=200,
        help_text="Service name"
    )
    
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        help_text="Service category"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Service description"
    )
    
    base_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Base price in NGN"
    )
    
    # Package pricing
    is_package = models.BooleanField(
        default=False,
        help_text="Is this a package deal?"
    )
    
    package_includes = models.JSONField(
        default=list,
        blank=True,
        help_text="Services included in package"
    )
    
    # Insurance
    insurance_covered = models.BooleanField(
        default=False,
        help_text="Typically covered by insurance"
    )
    
    insurance_code = models.CharField(
        max_length=50,
        blank=True,
        help_text="Insurance billing code"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Is this service currently offered"
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ivf_price_list'
        ordering = ['category', 'name']
        verbose_name = 'IVF Price List Item'
        verbose_name_plural = 'IVF Price List'
    
    def __str__(self):
        return f"{self.name} - ₦{self.base_price:,.2f}"


class IVFCycleCharge(models.Model):
    """
    IVF Cycle Charges
    
    Tracks all charges associated with an IVF cycle.
    Separate from standard VisitCharge as IVF cycles span multiple visits.
    """
    
    cycle = models.ForeignKey(
        'ivf.IVFCycle',
        on_delete=models.CASCADE,
        related_name='charges'
    )
    
    service = models.ForeignKey(
        IVFPriceList,
        on_delete=models.PROTECT,
        related_name='charges'
    )
    
    description = models.CharField(
        max_length=255,
        help_text="Charge description"
    )
    
    quantity = models.PositiveIntegerField(
        default=1,
        help_text="Quantity of service"
    )
    
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Unit price at time of charge"
    )
    
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Total charge amount"
    )
    
    # Discount
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Discount percentage"
    )
    
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Discount amount"
    )
    
    final_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Final amount after discount"
    )
    
    # Insurance
    insurance_claim_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Amount claimed from insurance"
    )
    
    patient_responsibility = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Amount patient must pay"
    )
    
    # Payment status
    is_paid = models.BooleanField(
        default=False,
        help_text="Has this charge been paid"
    )
    
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When charge was paid"
    )
    
    # Reference to related records
    stimulation_record = models.ForeignKey(
        'ivf.OvarianStimulation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='charges'
    )
    
    retrieval = models.ForeignKey(
        'ivf.OocyteRetrieval',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='charges'
    )
    
    transfer = models.ForeignKey(
        'ivf.EmbryoTransfer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='charges'
    )
    
    embryo = models.ForeignKey(
        'ivf.Embryo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='charges'
    )
    
    sperm_analysis = models.ForeignKey(
        'ivf.SpermAnalysis',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='charges'
    )
    
    medication = models.ForeignKey(
        'ivf.IVFMedication',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='charges'
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Billing notes"
    )
    
    # Audit
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='ivf_charges_created'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ivf_cycle_charges'
        ordering = ['-created_at']
        verbose_name = 'IVF Cycle Charge'
        verbose_name_plural = 'IVF Cycle Charges'
    
    def __str__(self):
        return f"{self.description} - ₦{self.final_amount:,.2f}"
    
    def save(self, *args, **kwargs):
        # Calculate totals
        self.total_amount = self.unit_price * self.quantity
        
        # Apply discount
        if self.discount_percent > 0:
            self.discount_amount = self.total_amount * (self.discount_percent / 100)
        
        self.final_amount = self.total_amount - self.discount_amount
        
        # Calculate patient responsibility
        self.patient_responsibility = self.final_amount - self.insurance_claim_amount
        
        super().save(*args, **kwargs)


class IVFPaymentPlan(models.Model):
    """
    IVF Payment Plan
    
    Allows patients to pay for expensive IVF cycles in installments.
    Nigerian healthcare context: Many families need payment plans for IVF.
    """
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('DEFAULTED', 'Defaulted'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    cycle = models.OneToOneField(
        'ivf.IVFCycle',
        on_delete=models.CASCADE,
        related_name='payment_plan'
    )
    
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Total amount to be paid"
    )
    
    down_payment = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Initial down payment"
    )
    
    number_of_installments = models.PositiveIntegerField(
        help_text="Number of installment payments"
    )
    
    installment_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Amount per installment"
    )
    
    total_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Total amount paid so far"
    )
    
    remaining_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Remaining balance"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE'
    )
    
    start_date = models.DateField(
        help_text="Plan start date"
    )
    
    next_payment_date = models.DateField(
        null=True,
        blank=True,
        help_text="Next payment due date"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Payment plan notes"
    )
    
    # Audit
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='ivf_payment_plans_created'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ivf_payment_plans'
        verbose_name = 'IVF Payment Plan'
        verbose_name_plural = 'IVF Payment Plans'
    
    def __str__(self):
        return f"Payment Plan - Cycle {self.cycle_id} - ₦{self.remaining_balance:,.2f} remaining"
    
    def save(self, *args, **kwargs):
        self.remaining_balance = self.total_amount - self.total_paid
        super().save(*args, **kwargs)
    
    def record_payment(self, amount, user):
        """Record a payment against this plan."""
        self.total_paid += Decimal(str(amount))
        
        if self.total_paid >= self.total_amount:
            self.status = 'COMPLETED'
            self.remaining_balance = Decimal('0.00')
        else:
            self.remaining_balance = self.total_amount - self.total_paid
            # Calculate next payment date (30 days from now)
            self.next_payment_date = timezone.now().date() + timezone.timedelta(days=30)
        
        self.save()
        
        # Create payment record
        return IVFPaymentRecord.objects.create(
            payment_plan=self,
            amount=amount,
            payment_date=timezone.now().date(),
            recorded_by=user
        )


class IVFPaymentRecord(models.Model):
    """
    Individual payment records for IVF payment plans.
    """
    
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('POS', 'POS'),
        ('TRANSFER', 'Bank Transfer'),
        ('PAYSTACK', 'Paystack'),
        ('WALLET', 'Wallet'),
    ]
    
    payment_plan = models.ForeignKey(
        IVFPaymentPlan,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Payment amount"
    )
    
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='CASH'
    )
    
    payment_date = models.DateField(
        help_text="Date payment was made"
    )
    
    transaction_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Transaction reference"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Payment notes"
    )
    
    # Audit
    recorded_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='ivf_payments_recorded'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ivf_payment_records'
        ordering = ['-payment_date']
        verbose_name = 'IVF Payment Record'
        verbose_name_plural = 'IVF Payment Records'
    
    def __str__(self):
        return f"Payment ₦{self.amount:,.2f} on {self.payment_date}"


# Service functions for creating charges

def create_cycle_package_charge(cycle, package_code, user, discount_percent=0):
    """Create a charge for an IVF cycle package."""
    try:
        package = IVFPriceList.objects.get(code=package_code, is_active=True)
    except IVFPriceList.DoesNotExist:
        raise ValueError(f"Package {package_code} not found")
    
    return IVFCycleCharge.objects.create(
        cycle=cycle,
        service=package,
        description=f"IVF Cycle Package - {package.name}",
        quantity=1,
        unit_price=package.base_price,
        discount_percent=discount_percent,
        created_by=user
    )


def create_retrieval_charge(cycle, retrieval, user):
    """Create a charge for oocyte retrieval procedure."""
    try:
        service = IVFPriceList.objects.get(
            category=IVFServiceCategory.RETRIEVAL,
            is_active=True
        )
    except IVFPriceList.DoesNotExist:
        # Use default price if no service defined
        service = None
    
    return IVFCycleCharge.objects.create(
        cycle=cycle,
        service=service,
        description=f"Oocyte Retrieval - {retrieval.total_oocytes_retrieved} oocytes",
        quantity=1,
        unit_price=service.base_price if service else Decimal('350000.00'),
        retrieval=retrieval,
        created_by=user
    )


def create_transfer_charge(cycle, transfer, user):
    """Create a charge for embryo transfer procedure."""
    try:
        service = IVFPriceList.objects.get(
            category=IVFServiceCategory.TRANSFER,
            is_active=True
        )
    except IVFPriceList.DoesNotExist:
        service = None
    
    return IVFCycleCharge.objects.create(
        cycle=cycle,
        service=service,
        description=f"Embryo Transfer - {transfer.embryos_transferred_count} embryo(s)",
        quantity=1,
        unit_price=service.base_price if service else Decimal('150000.00'),
        transfer=transfer,
        created_by=user
    )


def create_cryopreservation_charge(cycle, embryo, user):
    """Create a charge for embryo cryopreservation."""
    try:
        service = IVFPriceList.objects.get(
            category=IVFServiceCategory.CRYOPRESERVATION,
            is_active=True
        )
    except IVFPriceList.DoesNotExist:
        service = None
    
    return IVFCycleCharge.objects.create(
        cycle=cycle,
        service=service,
        description=f"Embryo Cryopreservation - {embryo.lab_id}",
        quantity=1,
        unit_price=service.base_price if service else Decimal('100000.00'),
        embryo=embryo,
        created_by=user
    )


def create_pgt_charge(cycle, embryo, user):
    """Create a charge for preimplantation genetic testing."""
    try:
        service = IVFPriceList.objects.get(
            category=IVFServiceCategory.PGT,
            is_active=True
        )
    except IVFPriceList.DoesNotExist:
        service = None
    
    return IVFCycleCharge.objects.create(
        cycle=cycle,
        service=service,
        description=f"PGT Testing - {embryo.lab_id}",
        quantity=1,
        unit_price=service.base_price if service else Decimal('200000.00'),
        embryo=embryo,
        created_by=user
    )


def get_cycle_billing_summary(cycle):
    """Get billing summary for an IVF cycle."""
    charges = IVFCycleCharge.objects.filter(cycle=cycle)
    
    total_charges = sum(c.final_amount for c in charges)
    total_paid = sum(c.final_amount for c in charges if c.is_paid)
    insurance_total = sum(c.insurance_claim_amount for c in charges)
    patient_total = sum(c.patient_responsibility for c in charges)
    
    # Check for payment plan
    payment_plan = getattr(cycle, 'payment_plan', None)
    
    return {
        'total_charges': total_charges,
        'total_paid': total_paid,
        'outstanding_balance': total_charges - total_paid,
        'insurance_claimed': insurance_total,
        'patient_responsibility': patient_total,
        'charges_count': charges.count(),
        'has_payment_plan': payment_plan is not None,
        'payment_plan_status': payment_plan.status if payment_plan else None,
        'next_payment_date': payment_plan.next_payment_date if payment_plan else None,
    }

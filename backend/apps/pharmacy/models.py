"""
Prescription and Drug models - strictly visit-scoped and consultation-dependent.

Per EMR Rules:
- Prescriptions CANNOT exist without Consultation
- Prescriptions CANNOT exist without Visit
- Doctor creates prescriptions
- Pharmacist dispenses medication
- Pharmacist manages drug catalog
- Doctor views prescriptions
"""
from django.db import models
from django.core.exceptions import ValidationError


class Drug(models.Model):
    """
    Drug/Medication catalog model - managed by Pharmacists.
    
    Design Principles:
    1. Pharmacist-only creation/management
    2. Drug catalog for reference when creating prescriptions
    3. Contains drug information: name, code, dosage forms, etc.
    4. Audit logging for all changes
    """
    
    # Basic drug information
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Name of the drug/medication (e.g., 'Paracetamol', 'Amoxicillin')"
    )
    
    generic_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Generic name of the drug"
    )
    
    drug_code = models.CharField(
        max_length=100,
        blank=True,
        unique=True,
        null=True,
        help_text="Drug code/identifier (e.g., NDC code, internal code)"
    )
    
    # Drug classification
    drug_class = models.CharField(
        max_length=255,
        blank=True,
        help_text="Drug classification (e.g., 'Antibiotic', 'Analgesic', 'Antihypertensive')"
    )
    
    # Dosage forms available
    dosage_forms = models.CharField(
        max_length=255,
        blank=True,
        help_text="Available dosage forms (e.g., 'Tablet, Capsule, Syrup')"
    )
    
    # Common dosages
    common_dosages = models.CharField(
        max_length=255,
        blank=True,
        help_text="Common dosages (e.g., '250mg, 500mg, 1000mg')"
    )
    
    # Pricing information
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Cost price (purchase price) of the drug"
    )
    
    sales_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Sales price (selling price) of the drug"
    )
    
    # Additional information
    description = models.TextField(
        blank=True,
        help_text="Description of the drug, indications, etc."
    )
    
    # Status tracking
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the drug is currently available/active"
    )
    
    # User tracking
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='drugs_created',
        help_text="Pharmacist who created this drug entry"
    )
    
    # Audit timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the drug entry was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the drug entry was last updated"
    )
    
    class Meta:
        db_table = 'drugs'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['drug_code']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_by']),
        ]
        verbose_name = 'Drug'
        verbose_name_plural = 'Drugs'
    
    def __str__(self):
        return self.name
    
    def clean(self):
        """Validation: Ensure drug name is provided and prices are valid."""
        if not self.name or not self.name.strip():
            raise ValidationError("Drug name is required.")
        
        # Validate pricing
        if self.cost_price is not None and self.cost_price < 0:
            raise ValidationError("Cost price cannot be negative.")
        
        if self.sales_price is not None and self.sales_price < 0:
            raise ValidationError("Sales price cannot be negative.")
        
        if self.cost_price is not None and self.sales_price is not None:
            if self.sales_price < self.cost_price:
                raise ValidationError("Sales price should not be less than cost price.")
    
    @property
    def profit(self):
        """Calculate profit (sales_price - cost_price)."""
        if self.cost_price is not None and self.sales_price is not None:
            return self.sales_price - self.cost_price
        return None
    
    @property
    def profit_margin(self):
        """Calculate profit margin percentage."""
        if self.cost_price is not None and self.sales_price is not None and self.cost_price > 0:
            return ((self.sales_price - self.cost_price) / self.cost_price) * 100
        return None
    
    def save(self, *args, **kwargs):
        """Override save to run clean() validation."""
        self.full_clean()
        super().save(*args, **kwargs)


class DrugInventory(models.Model):
    """
    Drug Inventory model - tracks stock levels for drugs.
    
    Design Principles:
    1. One inventory record per drug (OneToOne with Drug)
    2. Tracks current stock quantity
    3. Reorder level for low stock alerts
    4. Unit of measurement
    5. Optional batch/lot tracking
    6. Optional expiry date tracking
    7. Pharmacist-only management
    """
    
    # Core relationship - One inventory per drug
    drug = models.OneToOneField(
        'pharmacy.Drug',
        on_delete=models.CASCADE,
        related_name='inventory',
        help_text="Drug for this inventory record"
    )
    
    # Stock information
    current_stock = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Current stock quantity"
    )
    
    unit = models.CharField(
        max_length=50,
        default='units',
        help_text="Unit of measurement (e.g., 'tablets', 'bottles', 'vials', 'units')"
    )
    
    reorder_level = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Reorder level - alert when stock falls below this"
    )
    
    # Optional batch/lot tracking
    batch_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Batch or lot number (optional)"
    )
    
    expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text="Expiry date (optional)"
    )
    
    # Location tracking (optional)
    location = models.CharField(
        max_length=255,
        blank=True,
        help_text="Storage location (e.g., 'Shelf A1', 'Refrigerator 1')"
    )
    
    # Last restocked information
    last_restocked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the inventory was last restocked"
    )
    
    last_restocked_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='inventory_restocked',
        null=True,
        blank=True,
        help_text="User who last restocked this inventory"
    )
    
    # Audit timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the inventory record was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the inventory record was last updated"
    )
    
    class Meta:
        db_table = 'drug_inventory'
        ordering = ['drug__name']
        indexes = [
            models.Index(fields=['drug']),
            models.Index(fields=['current_stock']),
            models.Index(fields=['reorder_level']),
        ]
        verbose_name = 'Drug Inventory'
        verbose_name_plural = 'Drug Inventories'
    
    def __str__(self):
        return f"{self.drug.name} - {self.current_stock} {self.unit}"
    
    @property
    def is_low_stock(self):
        """Check if stock is below reorder level."""
        return self.current_stock <= self.reorder_level
    
    @property
    def is_out_of_stock(self):
        """Check if stock is zero or negative."""
        return self.current_stock <= 0
    
    def clean(self):
        """Validation: Ensure stock and reorder level are non-negative."""
        if self.current_stock < 0:
            raise ValidationError("Current stock cannot be negative.")
        if self.reorder_level < 0:
            raise ValidationError("Reorder level cannot be negative.")
    
    def save(self, *args, **kwargs):
        """Override save to run clean() validation."""
        self.full_clean()
        super().save(*args, **kwargs)


class StockMovement(models.Model):
    """
    Stock Movement model - tracks all inventory changes.
    
    Design Principles:
    1. Tracks all stock movements (in, out, adjustments)
    2. Links to inventory record
    3. Optional link to prescription (for dispensed items)
    4. Audit logging mandatory
    5. Immutable records (no updates/deletes)
    """
    
    MOVEMENT_TYPES = [
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
        ('ADJUSTMENT', 'Adjustment'),
        ('DISPENSED', 'Dispensed'),
        ('RETURNED', 'Returned'),
        ('EXPIRED', 'Expired'),
        ('DAMAGED', 'Damaged'),
    ]
    
    # Core relationship
    inventory = models.ForeignKey(
        'pharmacy.DrugInventory',
        on_delete=models.CASCADE,
        related_name='movements',
        help_text="Inventory record for this movement"
    )
    
    # Movement details
    movement_type = models.CharField(
        max_length=20,
        choices=MOVEMENT_TYPES,
        help_text="Type of stock movement"
    )
    
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Quantity moved (positive for IN, negative for OUT)"
    )
    
    # Reference information
    prescription = models.ForeignKey(
        'pharmacy.Prescription',
        on_delete=models.SET_NULL,
        related_name='stock_movements',
        null=True,
        blank=True,
        help_text="Prescription linked to this movement (if dispensed)"
    )
    
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Reference number (e.g., invoice number, adjustment ID)"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this movement"
    )
    
    # User tracking
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='stock_movements',
        help_text="User who created this movement"
    )
    
    # Audit timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the movement was recorded"
    )
    
    class Meta:
        db_table = 'stock_movements'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['inventory']),
            models.Index(fields=['movement_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['prescription']),
        ]
        verbose_name = 'Stock Movement'
        verbose_name_plural = 'Stock Movements'
    
    def __str__(self):
        return f"{self.movement_type} - {self.quantity} {self.inventory.unit} - {self.inventory.drug.name}"
    
    def clean(self):
        """Validation: Ensure quantity is appropriate for movement type."""
        if self.movement_type in ['IN', 'RETURNED'] and self.quantity <= 0:
            raise ValidationError("Stock IN and RETURNED movements must have positive quantity.")
        if self.movement_type in ['OUT', 'DISPENSED', 'EXPIRED', 'DAMAGED'] and self.quantity >= 0:
            raise ValidationError("Stock OUT, DISPENSED, EXPIRED, and DAMAGED movements must have negative quantity.")
        if self.movement_type == 'ADJUSTMENT' and self.quantity == 0:
            raise ValidationError("Adjustment quantity cannot be zero.")
    
    def save(self, *args, **kwargs):
        """Override save to update inventory and run validation."""
        self.full_clean()
        
        # Update inventory stock
        if self.pk is None:  # New movement
            if self.movement_type in ['IN', 'RETURNED']:
                self.inventory.current_stock += abs(self.quantity)
            elif self.movement_type in ['OUT', 'DISPENSED', 'EXPIRED', 'DAMAGED']:
                self.inventory.current_stock -= abs(self.quantity)
            elif self.movement_type == 'ADJUSTMENT':
                self.inventory.current_stock += self.quantity
            
            # Update last restocked if it's a stock IN
            if self.movement_type == 'IN':
                from django.utils import timezone
                self.inventory.last_restocked_at = timezone.now()
                self.inventory.last_restocked_by = self.created_by
                self.inventory.save(update_fields=['current_stock', 'last_restocked_at', 'last_restocked_by'])
            else:
                self.inventory.save(update_fields=['current_stock'])
        
        super().save(*args, **kwargs)


class Prescription(models.Model):
    """
    Prescription model - visit-scoped and consultation-dependent.
    
    Design Principles:
    1. ForeignKey to Visit - visit-scoped
    2. ForeignKey to Consultation - consultation-dependent (REQUIRED)
    3. Doctor creates prescriptions (prescribed_by)
    4. Pharmacist dispenses medication (dispensed_by)
    5. Status tracking: PENDING, DISPENSED, CANCELLED
    """
    
    # Core relationships - ABSOLUTE: Cannot exist without Visit and Consultation
    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.CASCADE,
        related_name='prescriptions',
        help_text="Visit is the single source of clinical truth. Prescription is visit-scoped."
    )
    
    consultation = models.ForeignKey(
        'consultations.Consultation',
        on_delete=models.CASCADE,
        related_name='prescriptions',
        help_text="Prescription requires consultation context. Cannot exist without consultation.",
        null=False,  # Explicitly enforce NOT NULL at database level
        blank=False,  # Explicitly enforce required at form level
    )
    
    # Emergency override flag (Nigerian clinic operational reality)
    is_emergency = models.BooleanField(
        default=False,
        help_text="Emergency flag: Allows dispensing without payment clearance. Requires proper authorization."
    )
    
    # Medication information
    drug = models.CharField(
        max_length=255,
        help_text="Name of the medication/drug"
    )
    
    drug_code = models.CharField(
        max_length=100,
        blank=True,
        help_text="Drug code/identifier (e.g., NDC code)"
    )
    
    dosage = models.CharField(
        max_length=255,
        help_text="Dosage instructions (e.g., '500mg twice daily')"
    )
    
    frequency = models.CharField(
        max_length=100,
        blank=True,
        help_text="Frequency of administration (e.g., 'BID', 'TID', 'QID')"
    )
    
    duration = models.CharField(
        max_length=100,
        blank=True,
        help_text="Duration of treatment (e.g., '7 days', '2 weeks')"
    )
    
    quantity = models.CharField(
        max_length=100,
        blank=True,
        help_text="Quantity prescribed (e.g., '30 tablets', '1 bottle')"
    )
    
    instructions = models.TextField(
        blank=True,
        help_text="Additional instructions for the patient"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        default='PENDING',
        choices=[
            ('PENDING', 'Pending'),
            ('DISPENSED', 'Dispensed'),
            ('CANCELLED', 'Cancelled'),
        ],
        help_text="Status of the prescription"
    )
    
    # Dispensing information (Pharmacist only)
    dispensed = models.BooleanField(
        default=False,
        help_text="Whether the medication has been dispensed"
    )
    
    dispensed_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the medication was dispensed"
    )
    
    dispensing_notes = models.TextField(
        blank=True,
        help_text="Notes from pharmacist during dispensing"
    )
    
    # User tracking
    prescribed_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='prescriptions_prescribed',
        help_text="Doctor who prescribed the medication"
    )
    
    dispensed_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='prescriptions_dispensed',
        null=True,
        blank=True,
        help_text="Pharmacist who dispensed the medication"
    )
    
    # Audit timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the prescription was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the prescription was last updated"
    )
    
    class Meta:
        db_table = 'prescriptions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['visit']),
            models.Index(fields=['consultation']),
            models.Index(fields=['status']),
            models.Index(fields=['prescribed_by']),
            models.Index(fields=['dispensed']),
        ]
        verbose_name = 'Prescription'
        verbose_name_plural = 'Prescriptions'
    
    def __str__(self):
        return f"Prescription {self.drug} for Visit {self.visit.id}"
    
    def clean(self):
        """
        Validation: Ensure consultation exists and visit is not CLOSED.
        
        Nigerian Clinic Governance Rules:
        1. Consultation is REQUIRED (enforced at database level)
        2. Visit must not be CLOSED
        3. Consultation must belong to same visit
        4. Payment must be cleared (unless emergency override)
        """
        if not self.visit_id:
            return
            
        if self.visit.status == 'CLOSED':
            raise ValidationError(
                "Cannot create or modify prescription for a CLOSED visit. "
                "Visit ID: %(visit_id)s is CLOSED. Closed visits are immutable per EMR governance rules."
            ) % {'visit_id': self.visit_id}
        
        # ❌ GOVERNANCE RULE: Consultation is REQUIRED
        if not self.consultation_id:
            raise ValidationError(
                "Prescriptions require a consultation. "
                "Per Nigerian clinic operational rules, all prescriptions must have clinical context from a consultation."
            )
        
        # Ensure consultation belongs to the same visit
        if self.consultation.visit_id != self.visit_id:
            raise ValidationError(
                f"Consultation must belong to the same visit as the prescription. "
                f"Consultation ID: {self.consultation_id} belongs to Visit ID: {self.consultation.visit_id}, "
                f"but this Prescription is for Visit ID: {self.visit_id}."
            )
        
        # ❌ Payment MUST be cleared (unless emergency)
        if not self.is_emergency and not self.visit.is_payment_cleared():
            raise ValidationError(
                f"Prescriptions require payment clearance. "
                f"Current payment status: {self.visit.payment_status}. "
                f"Please process payment before creating prescriptions. "
                f"For emergency cases, set is_emergency=True with proper authorization."
            )
    
    def save(self, *args, **kwargs):
        """Override save to run clean() validation."""
        self.full_clean()
        super().save(*args, **kwargs)


# --- E-Prescription (drug interaction-aware) ---


class Medication(models.Model):
    """
    Medication catalog for e-prescription with interaction data.
    """
    name = models.CharField(max_length=255, help_text="Brand/generic name")
    generic_name = models.CharField(max_length=255, blank=True)
    drug_class = models.CharField(max_length=255, blank=True)
    contraindications = models.TextField(blank=True)
    drug = models.OneToOneField(
        Drug,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='eprescription_medication',
        help_text="Link to pharmacy Drug if applicable",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'eprescription_medications'
        ordering = ['name']
        indexes = [models.Index(fields=['name']), models.Index(fields=['generic_name'])]

    def __str__(self):
        return self.name


class MedicationInteraction(models.Model):
    """Severity of interaction between two medications."""
    SEVERITY_CHOICES = [('Mild', 'Mild'), ('Moderate', 'Moderate'), ('Severe', 'Severe')]
    medication_a = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='interactions_from')
    medication_b = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='interactions_to')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='Moderate')
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'eprescription_medication_interactions'
        unique_together = [['medication_a', 'medication_b']]


class EPrescription(models.Model):
    """E-Prescription: patient, doctor, multiple medications with interaction check."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='eprescriptions',
    )
    doctor = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='eprescriptions',
    )
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    override_reason = models.TextField(
        blank=True,
        help_text="Doctor reason if interaction warning was overridden",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'eprescriptions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient']),
            models.Index(fields=['doctor']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"EPrescription {self.id} - {self.patient_id}"


class EPrescriptionItem(models.Model):
    """One medication line in an e-prescription."""
    eprescription = models.ForeignKey(
        EPrescription,
        on_delete=models.CASCADE,
        related_name='items',
    )
    medication = models.ForeignKey(
        Medication,
        on_delete=models.PROTECT,
        related_name='eprescription_items',
    )
    dosage = models.CharField(max_length=255)
    frequency = models.CharField(max_length=255, blank=True)
    duration = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'eprescription_items'
        unique_together = [['eprescription', 'medication']]
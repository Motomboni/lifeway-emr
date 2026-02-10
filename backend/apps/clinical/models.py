"""
Clinical models for vital signs, templates, and clinical decision support.
"""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError


class VitalSigns(models.Model):
    """
    Vital signs recorded during a visit.
    
    Per EMR Rules:
    - Visit-scoped: Must be associated with a visit
    - Can be recorded by doctors or nurses
    - Historical tracking for trend analysis
    """
    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.CASCADE,
        related_name='vital_signs',
        help_text="Visit this vital signs record belongs to"
    )
    
    recorded_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='vital_signs_recorded',
        help_text="User who recorded these vital signs"
    )
    
    # Vital signs measurements
    temperature = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(30.0), MaxValueValidator(45.0)],
        help_text="Body temperature in Celsius"
    )
    
    systolic_bp = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(50), MaxValueValidator(300)],
        help_text="Systolic blood pressure (mmHg)"
    )
    
    diastolic_bp = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(30), MaxValueValidator(200)],
        help_text="Diastolic blood pressure (mmHg)"
    )
    
    pulse = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(30), MaxValueValidator(250)],
        help_text="Heart rate (beats per minute)"
    )
    
    respiratory_rate = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(8), MaxValueValidator(50)],
        help_text="Respiratory rate (breaths per minute)"
    )
    
    oxygen_saturation = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Oxygen saturation (SpO2 %)"
    )
    
    weight = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.1), MaxValueValidator(500)],
        help_text="Weight in kilograms"
    )
    
    height = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.1), MaxValueValidator(300)],
        help_text="Height in centimeters"
    )
    
    bmi = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Body Mass Index (calculated)"
    )
    
    # Pediatric and Antenatal Care fields
    muac = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.1), MaxValueValidator(50)],
        help_text="Mid-Upper Arm Circumference (MUAC) in cm - for pediatrics"
    )
    
    nutritional_status = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('NORMAL', 'Normal'),
            ('UNDERWEIGHT', 'Underweight'),
            ('OVERWEIGHT', 'Overweight'),
            ('OBESE', 'Obese'),
            ('SEVERELY_UNDERWEIGHT', 'Severely Underweight'),
            ('MALNOURISHED', 'Malnourished'),
        ],
        help_text="Nutritional status assessment"
    )
    
    urine_anc = models.CharField(
        max_length=100,
        blank=True,
        help_text="Urine test results for Antenatal Care (e.g., Protein, Glucose, Leukocytes)"
    )
    
    lmp = models.DateField(
        null=True,
        blank=True,
        help_text="Last Menstrual Period (LMP)"
    )
    
    edd = models.DateField(
        null=True,
        blank=True,
        help_text="Expected Due Date (EDD)"
    )
    
    ega_weeks = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(45)],
        help_text="Estimated Gestational Age in weeks"
    )
    
    ega_days = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(6)],
        help_text="Estimated Gestational Age additional days (0-6)"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about vital signs"
    )
    
    # Timestamps
    recorded_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When vital signs were recorded"
    )
    
    class Meta:
        db_table = 'vital_signs'
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['visit', '-recorded_at']),
            models.Index(fields=['recorded_by']),
        ]
        verbose_name = 'Vital Signs'
        verbose_name_plural = 'Vital Signs'
    
    def __str__(self):
        return f"Vital Signs for Visit {self.visit_id} at {self.recorded_at}"
    
    def clean(self):
        """Validate vital signs data."""
        # Validate blood pressure
        if self.systolic_bp and self.diastolic_bp:
            if self.systolic_bp <= self.diastolic_bp:
                raise ValidationError("Systolic BP must be greater than diastolic BP")
        
        # Normalize height if provided in meters (e.g., 1.70 instead of 170 cm)
        if self.height is not None:
            try:
                height_val = Decimal(self.height)
                # Assume values less than 10 are meters; convert to centimeters
                if height_val > 0 and height_val < Decimal("10"):
                    self.height = (height_val * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            except (InvalidOperation, TypeError):
                # Leave height as-is; validation will catch non-numeric issues elsewhere
                pass

        # Calculate BMI if weight and height are provided
        if self.weight and self.height:
            try:
                height_m = Decimal(self.height) / Decimal("100")  # Convert cm to meters
                if height_m > 0:
                    bmi_val = Decimal(self.weight) / (height_m * height_m)
                    # Clamp unrealistic BMI values to avoid storage/serialization errors
                    if bmi_val > Decimal("999.99"):
                        self.bmi = None
                    else:
                        self.bmi = bmi_val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                else:
                    self.bmi = None
            except (InvalidOperation, TypeError, ZeroDivisionError):
                self.bmi = None
        else:
            self.bmi = None
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_abnormal_flags(self):
        """Return list of abnormal vital signs."""
        from decimal import Decimal, InvalidOperation
        
        flags = []
        
        # Temperature check - use Decimal for accurate comparison
        if self.temperature is not None:
            try:
                temp = Decimal(str(self.temperature))
                normal_min = Decimal('36.1')
                normal_max = Decimal('37.2')
                
                if temp < normal_min or temp > normal_max:
                    flags.append('FEVER' if temp > normal_max else 'HYPOTHERMIA')
            except (ValueError, InvalidOperation, TypeError):
                # Skip temperature check if conversion fails
                pass
        
        # Blood pressure check
        if self.systolic_bp is not None and self.diastolic_bp is not None:
            if self.systolic_bp > 140 or self.diastolic_bp > 90:
                flags.append('HYPERTENSION')
            elif self.systolic_bp < 90 or self.diastolic_bp < 60:
                flags.append('HYPOTENSION')
        
        # Pulse check
        if self.pulse is not None:
            if self.pulse > 100:
                flags.append('TACHYCARDIA')
            elif self.pulse < 60:
                flags.append('BRADYCARDIA')
        
        # Respiratory rate check
        if self.respiratory_rate is not None:
            if self.respiratory_rate > 20:
                flags.append('TACHYPNEA')
            elif self.respiratory_rate < 12:
                flags.append('BRADYPNEA')
        
        # Oxygen saturation check - use Decimal for accurate comparison
        if self.oxygen_saturation is not None:
            try:
                spo2 = Decimal(str(self.oxygen_saturation))
                if spo2 < Decimal('95'):
                    flags.append('HYPOXIA')
            except (ValueError, InvalidOperation, TypeError):
                # Skip oxygen saturation check if conversion fails
                pass
        
        # BMI check - use Decimal for accurate comparison
        if self.bmi is not None:
            try:
                bmi_value = Decimal(str(self.bmi))
                if bmi_value < Decimal('18.5'):
                    flags.append('UNDERWEIGHT')
                elif bmi_value > Decimal('25'):
                    flags.append('OVERWEIGHT')
                if bmi_value > Decimal('30'):
                    flags.append('OBESE')
            except (ValueError, InvalidOperation, TypeError):
                # Skip BMI check if conversion fails
                pass
        
        return flags


class ClinicalTemplate(models.Model):
    """
    Pre-filled consultation templates for common conditions.
    
    Templates help doctors quickly document common conditions
    while maintaining clinical accuracy.
    """
    name = models.CharField(
        max_length=200,
        help_text="Template name (e.g., 'Common Cold', 'Hypertension Follow-up')"
    )
    
    category = models.CharField(
        max_length=100,
        help_text="Template category (e.g., 'General', 'Cardiology', 'Pediatrics')"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Description of when to use this template"
    )
    
    # Template content
    history_template = models.TextField(
        blank=True,
        help_text="Pre-filled history section"
    )
    
    examination_template = models.TextField(
        blank=True,
        help_text="Pre-filled examination section"
    )
    
    diagnosis_template = models.TextField(
        blank=True,
        help_text="Pre-filled diagnosis section"
    )
    
    clinical_notes_template = models.TextField(
        blank=True,
        help_text="Pre-filled clinical notes section"
    )
    
    # Metadata
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='clinical_templates_created',
        help_text="User who created this template"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this template is active and available for use"
    )
    
    usage_count = models.IntegerField(
        default=0,
        help_text="Number of times this template has been used"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'clinical_templates'
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['created_by']),
        ]
        verbose_name = 'Clinical Template'
        verbose_name_plural = 'Clinical Templates'
    
    def __str__(self):
        return f"{self.name} ({self.category})"
    
    def increment_usage(self):
        """Increment usage count."""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])


class ClinicalAlert(models.Model):
    """
    Clinical alerts for critical values, drug interactions, allergies.
    
    Alerts are generated automatically based on:
    - Vital signs outside normal ranges
    - Drug interactions
    - Known allergies
    - Critical lab values
    """
    ALERT_TYPES = [
        ('VITAL_SIGNS', 'Vital Signs Abnormal'),
        ('DRUG_INTERACTION', 'Drug Interaction'),
        ('ALLERGY', 'Allergy Warning'),
        ('LAB_CRITICAL', 'Critical Lab Value'),
        ('CONTRAINDICATION', 'Contraindication'),
        ('DOSAGE', 'Dosage Warning'),
    ]
    
    SEVERITY_LEVELS = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.CASCADE,
        related_name='clinical_alerts',
        help_text="Visit this alert is associated with"
    )
    
    alert_type = models.CharField(
        max_length=50,
        choices=ALERT_TYPES,
        help_text="Type of clinical alert"
    )
    
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_LEVELS,
        default='MEDIUM',
        help_text="Severity level of the alert"
    )
    
    title = models.CharField(
        max_length=200,
        help_text="Alert title"
    )
    
    message = models.TextField(
        help_text="Detailed alert message"
    )
    
    related_resource_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Type of related resource (e.g., 'prescription', 'vital_signs')"
    )
    
    related_resource_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="ID of related resource"
    )
    
    acknowledged_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alerts_acknowledged',
        help_text="User who acknowledged this alert"
    )
    
    acknowledged_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the alert was acknowledged"
    )
    
    is_resolved = models.BooleanField(
        default=False,
        help_text="Whether this alert has been resolved"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'clinical_alerts'
        ordering = ['-severity', '-created_at']
        indexes = [
            models.Index(fields=['visit', '-created_at']),
            models.Index(fields=['alert_type', 'is_resolved']),
            models.Index(fields=['severity', 'is_resolved']),
        ]
        verbose_name = 'Clinical Alert'
        verbose_name_plural = 'Clinical Alerts'
    
    def __str__(self):
        return f"{self.title} - {self.get_severity_display()} ({self.visit_id})"
    
    def acknowledge(self, user):
        """Mark alert as acknowledged."""
        self.acknowledged_by = user
        from django.utils import timezone
        self.acknowledged_at = timezone.now()
        self.save(update_fields=['acknowledged_by', 'acknowledged_at'])
    
    def resolve(self):
        """Mark alert as resolved."""
        self.is_resolved = True
        self.save(update_fields=['is_resolved'])

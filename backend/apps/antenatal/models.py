"""
Antenatal Clinic Management Models

Nigerian Healthcare Compliance:
- NHIA (National Health Insurance Authority) guidelines
- MDCN (Medical and Dental Council of Nigeria) standards
- Maternal and child health tracking
- Audit trails for all clinical actions

Per EMR Rules:
- Visit-scoped architecture (antenatal visits are linked to visits)
- Payment enforcement via PaymentClearedGuard
- Role-based access control
- Immutability of closed records
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal


class AntenatalRecord(models.Model):
    """
    Antenatal Record - tracks a complete pregnancy episode.
    
    A record tracks the pregnancy journey from booking through delivery.
    Each patient can have multiple antenatal records (multiple pregnancies).
    """
    
    class PregnancyOutcome(models.TextChoices):
        ONGOING = 'ONGOING', 'Ongoing Pregnancy'
        DELIVERED = 'DELIVERED', 'Delivered'
        MISCARRIAGE = 'MISCARRIAGE', 'Miscarriage'
        STILLBIRTH = 'STILLBIRTH', 'Stillbirth'
        TERMINATION = 'TERMINATION', 'Termination'
        ECTOPIC = 'ECTOPIC', 'Ectopic Pregnancy'
        MOLAR = 'MOLAR', 'Molar Pregnancy'
    
    class Parity(models.TextChoices):
        PRIMIGRAVIDA = 'PRIMIGRAVIDA', 'Primigravida (First Pregnancy)'
        MULTIGRAVIDA = 'MULTIGRAVIDA', 'Multigravida (2-4 Pregnancies)'
        GRAND_MULTIGRAVIDA = 'GRAND_MULTIGRAVIDA', 'Grand Multigravida (5+ Pregnancies)'
    
    # Patient information
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.PROTECT,
        related_name='antenatal_records',
        help_text="Patient (must be female)"
    )
    
    # Pregnancy identification
    pregnancy_number = models.PositiveIntegerField(
        default=1,
        help_text="Sequential pregnancy number for this patient"
    )
    
    # Booking information
    booking_date = models.DateField(
        help_text="Date of first antenatal visit (booking)"
    )
    
    lmp = models.DateField(
        help_text="Last Menstrual Period (LMP)"
    )
    
    edd = models.DateField(
        help_text="Expected Due Date (EDD) - calculated from LMP"
    )
    
    # Pregnancy details
    parity = models.CharField(
        max_length=20,
        choices=Parity.choices,
        default=Parity.PRIMIGRAVIDA,
        help_text="Parity classification"
    )
    
    gravida = models.PositiveIntegerField(
        default=1,
        help_text="Number of pregnancies (including current)"
    )
    
    para = models.PositiveIntegerField(
        default=0,
        help_text="Number of deliveries at 37+ weeks"
    )
    
    abortions = models.PositiveIntegerField(
        default=0,
        help_text="Number of abortions/miscarriages"
    )
    
    living_children = models.PositiveIntegerField(
        default=0,
        help_text="Number of living children"
    )
    
    # Medical history
    past_medical_history = models.TextField(
        blank=True,
        help_text="Past medical history relevant to pregnancy"
    )
    
    past_surgical_history = models.TextField(
        blank=True,
        help_text="Past surgical history"
    )
    
    family_history = models.TextField(
        blank=True,
        help_text="Family history relevant to pregnancy"
    )
    
    allergies = models.TextField(
        blank=True,
        help_text="Known allergies"
    )
    
    # Obstetric history
    previous_cs = models.BooleanField(
        default=False,
        help_text="Previous Cesarean Section"
    )
    
    previous_cs_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of previous Cesarean Sections"
    )
    
    previous_complications = models.TextField(
        blank=True,
        help_text="Previous pregnancy complications"
    )
    
    # Current pregnancy
    pregnancy_type = models.CharField(
        max_length=20,
        choices=[
            ('SINGLETON', 'Singleton'),
            ('TWINS', 'Twins'),
            ('TRIPLETS', 'Triplets'),
            ('MORE', 'More'),
        ],
        default='SINGLETON',
        help_text="Type of pregnancy"
    )
    
    # Risk factors
    high_risk = models.BooleanField(
        default=False,
        help_text="High-risk pregnancy flag"
    )
    
    risk_factors = models.JSONField(
        default=list,
        blank=True,
        help_text="List of risk factors (e.g., ['diabetes', 'hypertension', 'advanced_maternal_age'])"
    )
    
    # Outcome
    outcome = models.CharField(
        max_length=20,
        choices=PregnancyOutcome.choices,
        default=PregnancyOutcome.ONGOING,
        help_text="Pregnancy outcome"
    )
    
    delivery_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of delivery (if delivered)"
    )
    
    delivery_gestational_age_weeks = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Gestational age at delivery (weeks)"
    )
    
    delivery_gestational_age_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Gestational age at delivery (days)"
    )
    
    # Clinical notes
    clinical_notes = models.TextField(
        blank=True,
        help_text="General clinical notes"
    )
    
    # Audit
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='antenatal_records_created',
        help_text="User who created this record"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'antenatal_records'
        ordering = ['-booking_date', '-created_at']
        verbose_name = 'Antenatal Record'
        verbose_name_plural = 'Antenatal Records'
        indexes = [
            models.Index(fields=['patient', '-booking_date']),
            models.Index(fields=['outcome', '-booking_date']),
        ]
    
    def __str__(self):
        return f"Pregnancy #{self.pregnancy_number} - {self.patient.first_name} {self.patient.last_name}"
    
    def clean(self):
        """Validate antenatal record data."""
        if self.patient.gender != 'FEMALE':
            raise ValidationError("Antenatal records can only be created for female patients.")
        
        if self.edd and self.lmp:
            # EDD should be approximately 40 weeks from LMP
            from datetime import timedelta
            calculated_edd = self.lmp + timedelta(days=280)  # 40 weeks
            if abs((self.edd - calculated_edd).days) > 14:  # Allow 2 weeks variance
                raise ValidationError("EDD should be approximately 40 weeks (280 days) from LMP.")
        
        if self.delivery_date and self.booking_date:
            if self.delivery_date < self.booking_date:
                raise ValidationError("Delivery date cannot be before booking date.")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def current_gestational_age_weeks(self):
        """Calculate current gestational age in weeks."""
        if not self.lmp:
            return None
        from datetime import date
        today = date.today()
        if self.outcome != self.PregnancyOutcome.ONGOING:
            if self.delivery_date:
                today = self.delivery_date
            else:
                return None
        
        delta = today - self.lmp
        weeks = delta.days // 7
        return weeks
    
    @property
    def current_gestational_age_days(self):
        """Calculate current gestational age in days."""
        if not self.lmp:
            return None
        from datetime import date
        today = date.today()
        if self.outcome != self.PregnancyOutcome.ONGOING:
            if self.delivery_date:
                today = self.delivery_date
            else:
                return None
        
        delta = today - self.lmp
        days = delta.days % 7
        return days


class AntenatalVisit(models.Model):
    """
    Antenatal Visit - individual clinic visit during pregnancy.
    
    Each visit is linked to a Visit (for billing/visit management)
    and an AntenatalRecord (for pregnancy tracking).
    """
    
    class VisitType(models.TextChoices):
        BOOKING = 'BOOKING', 'Booking Visit'
        ROUTINE = 'ROUTINE', 'Routine Visit'
        EMERGENCY = 'EMERGENCY', 'Emergency Visit'
        FOLLOW_UP = 'FOLLOW_UP', 'Follow-up Visit'
        DELIVERY = 'DELIVERY', 'Delivery Visit'
    
    # Links
    antenatal_record = models.ForeignKey(
        AntenatalRecord,
        on_delete=models.CASCADE,
        related_name='visits',
        help_text="Antenatal record this visit belongs to"
    )
    
    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.CASCADE,
        related_name='antenatal_visits',
        help_text="Visit this antenatal visit is associated with"
    )
    
    # Visit details
    visit_date = models.DateField(
        help_text="Date of antenatal visit"
    )
    
    visit_type = models.CharField(
        max_length=20,
        choices=VisitType.choices,
        default=VisitType.ROUTINE,
        help_text="Type of antenatal visit"
    )
    
    gestational_age_weeks = models.PositiveIntegerField(
        help_text="Gestational age at visit (weeks)"
    )
    
    gestational_age_days = models.PositiveIntegerField(
        default=0,
        help_text="Gestational age at visit (days)"
    )
    
    # Chief complaint
    chief_complaint = models.TextField(
        blank=True,
        help_text="Chief complaint for this visit"
    )
    
    # Clinical assessment
    blood_pressure_systolic = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(50), MaxValueValidator(300)],
        help_text="Systolic BP (mmHg)"
    )
    
    blood_pressure_diastolic = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(30), MaxValueValidator(200)],
        help_text="Diastolic BP (mmHg)"
    )
    
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Weight (kg)"
    )
    
    fundal_height = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Fundal height (cm)"
    )
    
    fetal_heart_rate = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(100), MaxValueValidator(200)],
        help_text="Fetal heart rate (bpm)"
    )
    
    fetal_presentation = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('CEPHALIC', 'Cephalic'),
            ('BREECH', 'Breech'),
            ('TRANSVERSE', 'Transverse'),
            ('UNKNOWN', 'Unknown'),
        ],
        help_text="Fetal presentation"
    )
    
    # Urine test
    urine_protein = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('NEGATIVE', 'Negative'),
            ('TRACE', 'Trace'),
            ('1+', '1+'),
            ('2+', '2+'),
            ('3+', '3+'),
            ('4+', '4+'),
        ],
        help_text="Urine protein"
    )
    
    urine_glucose = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('NEGATIVE', 'Negative'),
            ('TRACE', 'Trace'),
            ('1+', '1+'),
            ('2+', '2+'),
            ('3+', '3+'),
            ('4+', '4+'),
        ],
        help_text="Urine glucose"
    )
    
    # Clinical notes
    clinical_notes = models.TextField(
        blank=True,
        help_text="Clinical notes for this visit"
    )
    
    # Next appointment
    next_appointment_date = models.DateField(
        null=True,
        blank=True,
        help_text="Next scheduled appointment date"
    )
    
    # Audit
    recorded_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='antenatal_visits_recorded',
        help_text="User who recorded this visit"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'antenatal_visits'
        ordering = ['-visit_date', '-created_at']
        verbose_name = 'Antenatal Visit'
        verbose_name_plural = 'Antenatal Visits'
        indexes = [
            models.Index(fields=['antenatal_record', '-visit_date']),
            models.Index(fields=['visit']),
        ]
    
    def __str__(self):
        return f"Visit {self.visit_date} - {self.antenatal_record}"


class AntenatalUltrasound(models.Model):
    """
    Ultrasound findings during antenatal care.
    """
    
    antenatal_visit = models.ForeignKey(
        AntenatalVisit,
        on_delete=models.CASCADE,
        related_name='ultrasounds',
        help_text="Antenatal visit this ultrasound belongs to"
    )
    
    scan_date = models.DateField(
        help_text="Date of ultrasound scan"
    )
    
    scan_type = models.CharField(
        max_length=20,
        choices=[
            ('DATING', 'Dating Scan'),
            ('NT', 'Nuchal Translucency'),
            ('ANATOMY', 'Anomaly Scan'),
            ('GROWTH', 'Growth Scan'),
            ('DOPPLER', 'Doppler Study'),
            ('BIOPHYSICAL', 'Biophysical Profile'),
            ('OTHER', 'Other'),
        ],
        help_text="Type of ultrasound scan"
    )
    
    gestational_age_weeks = models.PositiveIntegerField(
        help_text="Gestational age at scan (weeks)"
    )
    
    gestational_age_days = models.PositiveIntegerField(
        default=0,
        help_text="Gestational age at scan (days)"
    )
    
    # Fetal measurements
    crl = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Crown-Rump Length (mm)"
    )
    
    bpd = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Biparietal Diameter (mm)"
    )
    
    hc = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Head Circumference (mm)"
    )
    
    ac = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Abdominal Circumference (mm)"
    )
    
    fl = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Femur Length (mm)"
    )
    
    estimated_fetal_weight = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Estimated Fetal Weight (g)"
    )
    
    # Findings
    number_of_fetuses = models.PositiveIntegerField(
        default=1,
        help_text="Number of fetuses"
    )
    
    fetal_presentation = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('CEPHALIC', 'Cephalic'),
            ('BREECH', 'Breech'),
            ('TRANSVERSE', 'Transverse'),
            ('UNKNOWN', 'Unknown'),
        ],
        help_text="Fetal presentation"
    )
    
    placenta_location = models.CharField(
        max_length=50,
        blank=True,
        help_text="Placenta location"
    )
    
    placenta_grade = models.CharField(
        max_length=10,
        blank=True,
        choices=[
            ('0', 'Grade 0'),
            ('1', 'Grade 1'),
            ('2', 'Grade 2'),
            ('3', 'Grade 3'),
        ],
        help_text="Placenta grade"
    )
    
    amniotic_fluid = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('NORMAL', 'Normal'),
            ('OLIGOHYDRAMNIOS', 'Oligohydramnios'),
            ('POLYHYDRAMNIOS', 'Polyhydramnios'),
        ],
        help_text="Amniotic fluid assessment"
    )
    
    # Findings notes
    findings = models.TextField(
        blank=True,
        help_text="Ultrasound findings"
    )
    
    # Report
    report = models.TextField(
        blank=True,
        help_text="Ultrasound report"
    )
    
    # Audit
    performed_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='antenatal_ultrasounds_performed',
        help_text="User who performed/interpreted the scan"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'antenatal_ultrasounds'
        ordering = ['-scan_date', '-created_at']
        verbose_name = 'Antenatal Ultrasound'
        verbose_name_plural = 'Antenatal Ultrasounds'
    
    def __str__(self):
        return f"Ultrasound {self.scan_date} - {self.antenatal_visit}"


class AntenatalLab(models.Model):
    """
    Laboratory tests ordered during antenatal care.
    """
    
    antenatal_visit = models.ForeignKey(
        AntenatalVisit,
        on_delete=models.CASCADE,
        related_name='lab_tests',
        help_text="Antenatal visit this lab test belongs to"
    )
    
    test_name = models.CharField(
        max_length=255,
        help_text="Name of lab test"
    )
    
    test_date = models.DateField(
        help_text="Date test was ordered/performed"
    )
    
    # Common antenatal tests
    hb = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Hemoglobin (g/dL)"
    )
    
    pcv = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Packed Cell Volume (%)"
    )
    
    blood_group = models.CharField(
        max_length=10,
        blank=True,
        choices=[
            ('A+', 'A+'),
            ('A-', 'A-'),
            ('B+', 'B+'),
            ('B-', 'B-'),
            ('AB+', 'AB+'),
            ('AB-', 'AB-'),
            ('O+', 'O+'),
            ('O-', 'O-'),
        ],
        help_text="Blood group"
    )
    
    rhesus = models.CharField(
        max_length=10,
        blank=True,
        choices=[
            ('POSITIVE', 'Positive'),
            ('NEGATIVE', 'Negative'),
        ],
        help_text="Rhesus factor"
    )
    
    hiv = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('NEGATIVE', 'Negative'),
            ('POSITIVE', 'Positive'),
            ('PENDING', 'Pending'),
        ],
        help_text="HIV status"
    )
    
    hbsag = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('NEGATIVE', 'Negative'),
            ('POSITIVE', 'Positive'),
            ('PENDING', 'Pending'),
        ],
        help_text="HBsAg (Hepatitis B)"
    )
    
    vdrl = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('NEGATIVE', 'Negative'),
            ('POSITIVE', 'Positive'),
            ('PENDING', 'Pending'),
        ],
        help_text="VDRL (Syphilis)"
    )
    
    # Results
    results = models.TextField(
        blank=True,
        help_text="Test results (free text or structured)"
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        help_text="Notes about the test"
    )
    
    # Audit
    ordered_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='antenatal_labs_ordered',
        help_text="User who ordered the test"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'antenatal_labs'
        ordering = ['-test_date', '-created_at']
        verbose_name = 'Antenatal Lab Test'
        verbose_name_plural = 'Antenatal Lab Tests'
    
    def __str__(self):
        return f"{self.test_name} - {self.test_date}"


class AntenatalMedication(models.Model):
    """
    Medications prescribed during antenatal care.
    """
    
    antenatal_visit = models.ForeignKey(
        AntenatalVisit,
        on_delete=models.CASCADE,
        related_name='medications',
        help_text="Antenatal visit this medication belongs to"
    )
    
    medication_name = models.CharField(
        max_length=255,
        help_text="Name of medication"
    )
    
    category = models.CharField(
        max_length=50,
        choices=[
            ('FOLIC_ACID', 'Folic Acid'),
            ('IRON', 'Iron Supplement'),
            ('CALCIUM', 'Calcium Supplement'),
            ('MULTIVITAMIN', 'Multivitamin'),
            ('ANTIMALARIAL', 'Antimalarial'),
            ('ANTIBIOTIC', 'Antibiotic'),
            ('ANALGESIC', 'Analgesic'),
            ('ANTIHYPERTENSIVE', 'Antihypertensive'),
            ('ANTIDIABETIC', 'Antidiabetic'),
            ('OTHER', 'Other'),
        ],
        help_text="Medication category"
    )
    
    dose = models.CharField(
        max_length=100,
        help_text="Dose (e.g., '200mg', '1 tablet')"
    )
    
    frequency = models.CharField(
        max_length=100,
        help_text="Frequency (e.g., 'Once daily', 'Twice daily')"
    )
    
    duration = models.CharField(
        max_length=100,
        blank=True,
        help_text="Duration (e.g., '2 weeks', 'Until delivery')"
    )
    
    start_date = models.DateField(
        help_text="Start date"
    )
    
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="End date (if applicable)"
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        help_text="Notes about the medication"
    )
    
    # Audit
    prescribed_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='antenatal_medications_prescribed',
        help_text="User who prescribed the medication"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'antenatal_medications'
        ordering = ['-start_date', '-created_at']
        verbose_name = 'Antenatal Medication'
        verbose_name_plural = 'Antenatal Medications'
    
    def __str__(self):
        return f"{self.medication_name} - {self.antenatal_visit}"


class AntenatalOutcome(models.Model):
    """
    Delivery and pregnancy outcome information.
    """
    
    antenatal_record = models.OneToOneField(
        AntenatalRecord,
        on_delete=models.CASCADE,
        related_name='delivery_outcome',
        help_text="Antenatal record this outcome belongs to"
    )
    
    # Delivery information
    delivery_date = models.DateField(
        help_text="Date of delivery"
    )
    
    delivery_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Time of delivery"
    )
    
    delivery_type = models.CharField(
        max_length=20,
        choices=[
            ('VAGINAL', 'Vaginal Delivery'),
            ('VAGINAL_INSTRUMENTAL', 'Vaginal Instrumental'),
            ('CESAREAN_ELECTIVE', 'Elective Cesarean'),
            ('CESAREAN_EMERGENCY', 'Emergency Cesarean'),
        ],
        help_text="Type of delivery"
    )
    
    delivery_gestational_age_weeks = models.PositiveIntegerField(
        help_text="Gestational age at delivery (weeks)"
    )
    
    delivery_gestational_age_days = models.PositiveIntegerField(
        default=0,
        help_text="Gestational age at delivery (days)"
    )
    
    # Birth information
    number_of_babies = models.PositiveIntegerField(
        default=1,
        help_text="Number of babies delivered"
    )
    
    live_births = models.PositiveIntegerField(
        default=1,
        help_text="Number of live births"
    )
    
    stillbirths = models.PositiveIntegerField(
        default=0,
        help_text="Number of stillbirths"
    )
    
    # Baby details (for singleton, store in baby_1; for multiples, use JSON)
    baby_1_gender = models.CharField(
        max_length=10,
        blank=True,
        choices=[
            ('MALE', 'Male'),
            ('FEMALE', 'Female'),
        ],
        help_text="Baby 1 gender"
    )
    
    baby_1_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Baby 1 birth weight (kg)"
    )
    
    baby_1_apgar_1min = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Baby 1 APGAR at 1 minute"
    )
    
    baby_1_apgar_5min = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Baby 1 APGAR at 5 minutes"
    )
    
    # Additional babies (stored as JSON)
    additional_babies = models.JSONField(
        default=list,
        blank=True,
        help_text="Additional babies data [{'gender': 'FEMALE', 'weight': 2.5, 'apgar_1min': 8, 'apgar_5min': 9}]"
    )
    
    # Complications
    maternal_complications = models.TextField(
        blank=True,
        help_text="Maternal complications"
    )
    
    neonatal_complications = models.TextField(
        blank=True,
        help_text="Neonatal complications"
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about delivery and outcome"
    )
    
    # Audit
    recorded_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='antenatal_outcomes_recorded',
        help_text="User who recorded the outcome"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'antenatal_outcomes'
        verbose_name = 'Antenatal Outcome'
        verbose_name_plural = 'Antenatal Outcomes'
    
    def __str__(self):
        return f"Outcome - {self.antenatal_record}"

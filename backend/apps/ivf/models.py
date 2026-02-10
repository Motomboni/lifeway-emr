"""
IVF Treatment Module Models

Nigerian Healthcare Compliance:
- NHIA (National Health Insurance Authority) guidelines
- MDCN (Medical and Dental Council of Nigeria) standards
- Patient consent tracking for assisted reproduction
- Audit trails for all clinical actions
- Embryo custody and chain of custody tracking

Per EMR Rules:
- Visit-scoped architecture (IVF cycles can span multiple visits)
- Payment enforcement via PaymentClearedGuard
- Role-based access control (IVF_SPECIALIST role required)
- Immutability of closed records
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal


class IVFCycle(models.Model):
    """
    IVF Treatment Cycle - the primary container for an IVF treatment episode.
    
    A cycle tracks the complete IVF journey from initial assessment through
    embryo transfer and pregnancy outcome.
    
    Nigerian Compliance:
    - Requires documented consent before cycle start
    - Mandatory partner information for legal compliance
    - Insurance pre-authorization tracking
    """
    
    class CycleType(models.TextChoices):
        FRESH_IVF = 'FRESH_IVF', 'Fresh IVF Cycle'
        FROZEN_EMBRYO_TRANSFER = 'FET', 'Frozen Embryo Transfer'
        IUI = 'IUI', 'Intrauterine Insemination'
        ICSI = 'ICSI', 'Intracytoplasmic Sperm Injection'
        EGG_DONATION = 'EGG_DONATION', 'Egg Donation Cycle'
        SPERM_DONATION = 'SPERM_DONATION', 'Sperm Donation Cycle'
        SURROGACY = 'SURROGACY', 'Surrogacy Cycle'
        EGG_FREEZING = 'EGG_FREEZING', 'Egg Freezing (Oocyte Cryopreservation)'
        SPERM_FREEZING = 'SPERM_FREEZING', 'Sperm Freezing'
    
    class Status(models.TextChoices):
        PLANNED = 'PLANNED', 'Planned'
        STIMULATION = 'STIMULATION', 'Ovarian Stimulation'
        RETRIEVAL = 'RETRIEVAL', 'Egg Retrieval'
        FERTILIZATION = 'FERTILIZATION', 'Fertilization'
        CULTURE = 'CULTURE', 'Embryo Culture'
        TRANSFER = 'TRANSFER', 'Embryo Transfer'
        LUTEAL = 'LUTEAL', 'Luteal Phase Support'
        PREGNANCY_TEST = 'PREGNANCY_TEST', 'Pregnancy Test'
        PREGNANT = 'PREGNANT', 'Pregnant'
        NOT_PREGNANT = 'NOT_PREGNANT', 'Not Pregnant'
        CANCELLED = 'CANCELLED', 'Cancelled'
        COMPLETED = 'COMPLETED', 'Completed'
    
    class CancellationReason(models.TextChoices):
        POOR_RESPONSE = 'POOR_RESPONSE', 'Poor Ovarian Response'
        OHSS_RISK = 'OHSS_RISK', 'OHSS Risk'
        NO_FERTILIZATION = 'NO_FERTILIZATION', 'No Fertilization'
        NO_VIABLE_EMBRYOS = 'NO_VIABLE_EMBRYOS', 'No Viable Embryos'
        PATIENT_REQUEST = 'PATIENT_REQUEST', 'Patient Request'
        MEDICAL_CONTRAINDICATION = 'MEDICAL_CONTRAINDICATION', 'Medical Contraindication'
        FINANCIAL = 'FINANCIAL', 'Financial Reasons'
        OTHER = 'OTHER', 'Other'
    
    # Primary patient (female partner)
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.PROTECT,
        related_name='ivf_cycles',
        help_text="Primary patient (female partner in heterosexual couples)"
    )
    
    # Male partner (optional - for donation/single parent cases)
    partner = models.ForeignKey(
        'patients.Patient',
        on_delete=models.PROTECT,
        related_name='ivf_cycles_as_partner',
        null=True,
        blank=True,
        help_text="Male partner (if applicable)"
    )
    
    # Cycle identification
    cycle_number = models.PositiveIntegerField(
        default=1,
        help_text="Sequential cycle number for this patient"
    )
    
    cycle_type = models.CharField(
        max_length=20,
        choices=CycleType.choices,
        default=CycleType.FRESH_IVF,
        help_text="Type of IVF cycle"
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
        help_text="Current cycle status"
    )
    
    # Dates
    planned_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Planned cycle start date"
    )
    
    actual_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Actual stimulation start date"
    )
    
    lmp_date = models.DateField(
        null=True,
        blank=True,
        help_text="Last Menstrual Period date"
    )
    
    # Clinical Details
    protocol = models.CharField(
        max_length=100,
        blank=True,
        help_text="Stimulation protocol (e.g., Long GnRH agonist, Antagonist, Mini-IVF)"
    )
    
    diagnosis = models.TextField(
        blank=True,
        help_text="Infertility diagnosis"
    )
    
    # Consent Tracking (Nigerian Legal Requirement)
    consent_signed = models.BooleanField(
        default=False,
        help_text="Patient consent form signed"
    )
    
    consent_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date consent was signed"
    )
    
    partner_consent_signed = models.BooleanField(
        default=False,
        help_text="Partner consent form signed"
    )
    
    partner_consent_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date partner consent was signed"
    )
    
    # Cancellation
    cancellation_reason = models.CharField(
        max_length=30,
        choices=CancellationReason.choices,
        blank=True,
        help_text="Reason for cycle cancellation"
    )
    
    cancellation_notes = models.TextField(
        blank=True,
        help_text="Detailed notes on cancellation"
    )
    
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the cycle was cancelled"
    )
    
    # Outcome
    pregnancy_test_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of pregnancy test"
    )
    
    beta_hcg_result = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Beta-hCG result (mIU/mL)"
    )
    
    pregnancy_outcome = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('POSITIVE', 'Positive'),
            ('NEGATIVE', 'Negative'),
            ('CHEMICAL', 'Chemical Pregnancy'),
            ('ECTOPIC', 'Ectopic Pregnancy'),
            ('MISCARRIAGE', 'Miscarriage'),
            ('ONGOING', 'Ongoing Pregnancy'),
            ('LIVE_BIRTH', 'Live Birth'),
            ('STILLBIRTH', 'Stillbirth'),
        ],
        help_text="Final pregnancy outcome"
    )
    
    # Financial
    estimated_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Estimated total cycle cost (NGN)"
    )
    
    insurance_pre_auth = models.BooleanField(
        default=False,
        help_text="Insurance pre-authorization obtained"
    )
    
    insurance_pre_auth_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Insurance pre-authorization number"
    )
    
    # Notes
    clinical_notes = models.TextField(
        blank=True,
        help_text="Clinical notes and observations"
    )
    
    # Audit fields
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='ivf_cycles_created',
        help_text="User who created this cycle"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ivf_cycles'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient']),
            models.Index(fields=['partner']),
            models.Index(fields=['status']),
            models.Index(fields=['cycle_type']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'IVF Cycle'
        verbose_name_plural = 'IVF Cycles'
        unique_together = [['patient', 'cycle_number']]
    
    def __str__(self):
        return f"IVF Cycle #{self.cycle_number} - {self.patient} ({self.status})"
    
    def clean(self):
        """Validate cycle data."""
        # Consent required before starting cycle
        if self.status != self.Status.PLANNED and not self.consent_signed:
            raise ValidationError(
                "Patient consent must be signed before starting the cycle. "
                "This is a legal requirement under Nigerian healthcare regulations."
            )
        
        # Partner consent for certain cycle types
        if self.cycle_type in [self.CycleType.FRESH_IVF, self.CycleType.ICSI] and self.partner:
            if self.status != self.Status.PLANNED and not self.partner_consent_signed:
                raise ValidationError(
                    "Partner consent must be signed before starting the cycle."
                )
        
        # Cannot modify completed/cancelled cycles
        if self.pk:
            try:
                old = IVFCycle.objects.get(pk=self.pk)
                if old.status in [self.Status.COMPLETED, self.Status.CANCELLED]:
                    if self.status != old.status:
                        raise ValidationError(
                            "Cannot modify a completed or cancelled cycle."
                        )
            except IVFCycle.DoesNotExist:
                pass
    
    def save(self, *args, **kwargs):
        # Auto-increment cycle number for new cycles
        if not self.pk and not self.cycle_number:
            last_cycle = IVFCycle.objects.filter(patient=self.patient).order_by('-cycle_number').first()
            self.cycle_number = (last_cycle.cycle_number + 1) if last_cycle else 1
        
        self.full_clean()
        super().save(*args, **kwargs)
    
    def cancel(self, reason, notes='', user=None):
        """Cancel the cycle with proper audit trail."""
        if self.status in [self.Status.COMPLETED, self.Status.CANCELLED]:
            raise ValidationError("Cannot cancel an already completed or cancelled cycle.")
        
        self.status = self.Status.CANCELLED
        self.cancellation_reason = reason
        self.cancellation_notes = notes
        self.cancelled_at = timezone.now()
        self.save()


class OvarianStimulation(models.Model):
    """
    Ovarian Stimulation Protocol Tracking
    
    Tracks daily hormone levels and medication during stimulation phase.
    """
    
    cycle = models.ForeignKey(
        IVFCycle,
        on_delete=models.CASCADE,
        related_name='stimulation_records'
    )
    
    day = models.PositiveIntegerField(
        help_text="Stimulation day number"
    )
    
    date = models.DateField(
        help_text="Date of stimulation monitoring"
    )
    
    # Hormone Levels
    estradiol = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Estradiol level (pg/mL)"
    )
    
    lh = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="LH level (mIU/mL)"
    )
    
    progesterone = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Progesterone level (ng/mL)"
    )
    
    # Ultrasound Findings
    endometrial_thickness = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Endometrial thickness (mm)"
    )
    
    endometrial_pattern = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('TRILAMINAR', 'Trilaminar'),
            ('HYPERECHOIC', 'Hyperechoic'),
            ('HYPOECHOIC', 'Hypoechoic'),
            ('HOMOGENEOUS', 'Homogeneous'),
        ],
        help_text="Endometrial pattern on ultrasound"
    )
    
    # Follicle Counts (JSON for flexibility)
    right_ovary_follicles = models.JSONField(
        default=list,
        blank=True,
        help_text="Right ovary follicle sizes (mm) as array"
    )
    
    left_ovary_follicles = models.JSONField(
        default=list,
        blank=True,
        help_text="Left ovary follicle sizes (mm) as array"
    )
    
    # Medications administered
    medications = models.JSONField(
        default=list,
        blank=True,
        help_text="Medications with doses [{'name': 'Gonal-F', 'dose': 150, 'unit': 'IU'}]"
    )
    
    # Clinical Assessment
    notes = models.TextField(
        blank=True,
        help_text="Clinical notes for the day"
    )
    
    next_appointment = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Next monitoring appointment"
    )
    
    # Audit
    recorded_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='stimulation_records'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ivf_ovarian_stimulation'
        ordering = ['cycle', 'day']
        unique_together = [['cycle', 'day']]
        verbose_name = 'Ovarian Stimulation Record'
        verbose_name_plural = 'Ovarian Stimulation Records'
    
    def __str__(self):
        return f"Day {self.day} - Cycle {self.cycle_id}"
    
    @property
    def total_follicle_count(self):
        """Total follicle count from both ovaries."""
        return len(self.right_ovary_follicles or []) + len(self.left_ovary_follicles or [])
    
    @property
    def leading_follicles(self):
        """Count of follicles >= 14mm."""
        all_follicles = (self.right_ovary_follicles or []) + (self.left_ovary_follicles or [])
        return len([f for f in all_follicles if f >= 14])


class OocyteRetrieval(models.Model):
    """
    Oocyte (Egg) Retrieval Procedure
    
    Records the egg collection procedure details and outcomes.
    """
    
    cycle = models.OneToOneField(
        IVFCycle,
        on_delete=models.CASCADE,
        related_name='oocyte_retrieval'
    )
    
    # Procedure Details
    procedure_date = models.DateField(
        help_text="Date of egg retrieval"
    )
    
    procedure_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Time procedure started"
    )
    
    trigger_medication = models.CharField(
        max_length=100,
        blank=True,
        help_text="Trigger medication used (e.g., hCG, GnRH agonist)"
    )
    
    trigger_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Time of trigger injection"
    )
    
    # Anesthesia
    anesthesia_type = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('NONE', 'None'),
            ('LOCAL', 'Local'),
            ('CONSCIOUS_SEDATION', 'Conscious Sedation'),
            ('GENERAL', 'General Anesthesia'),
        ],
        help_text="Type of anesthesia used"
    )
    
    anesthesiologist = models.CharField(
        max_length=100,
        blank=True,
        help_text="Anesthesiologist name"
    )
    
    # Retrieval Results
    right_ovary_oocytes = models.PositiveIntegerField(
        default=0,
        help_text="Oocytes retrieved from right ovary"
    )
    
    left_ovary_oocytes = models.PositiveIntegerField(
        default=0,
        help_text="Oocytes retrieved from left ovary"
    )
    
    total_oocytes_retrieved = models.PositiveIntegerField(
        default=0,
        help_text="Total oocytes retrieved"
    )
    
    mature_oocytes = models.PositiveIntegerField(
        default=0,
        help_text="Number of mature (MII) oocytes"
    )
    
    immature_oocytes = models.PositiveIntegerField(
        default=0,
        help_text="Number of immature oocytes"
    )
    
    degenerated_oocytes = models.PositiveIntegerField(
        default=0,
        help_text="Number of degenerated oocytes"
    )
    
    # Complications
    complications = models.TextField(
        blank=True,
        help_text="Any complications during procedure"
    )
    
    blood_loss = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('MINIMAL', 'Minimal'),
            ('MODERATE', 'Moderate'),
            ('SIGNIFICANT', 'Significant'),
        ],
        help_text="Estimated blood loss"
    )
    
    # Post-procedure
    recovery_notes = models.TextField(
        blank=True,
        help_text="Post-procedure recovery notes"
    )
    
    discharge_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Time patient discharged"
    )
    
    # Performing doctor
    performed_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='oocyte_retrievals'
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ivf_oocyte_retrieval'
        verbose_name = 'Oocyte Retrieval'
        verbose_name_plural = 'Oocyte Retrievals'
    
    def __str__(self):
        return f"Retrieval - {self.total_oocytes_retrieved} oocytes - Cycle {self.cycle_id}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate total
        self.total_oocytes_retrieved = self.right_ovary_oocytes + self.left_ovary_oocytes
        super().save(*args, **kwargs)


class SpermAnalysis(models.Model):
    """
    Sperm Analysis / Semen Analysis
    
    Records semen analysis parameters per WHO 2021 guidelines.
    Can be linked to a cycle or standalone for initial assessment.
    """
    
    class SampleSource(models.TextChoices):
        FRESH_EJACULATE = 'FRESH', 'Fresh Ejaculate'
        FROZEN = 'FROZEN', 'Frozen Sample'
        SURGICAL_TESE = 'TESE', 'Testicular Sperm Extraction'
        SURGICAL_MESA = 'MESA', 'Microsurgical Epididymal Sperm Aspiration'
        SURGICAL_PESA = 'PESA', 'Percutaneous Epididymal Sperm Aspiration'
        DONOR = 'DONOR', 'Donor Sperm'
    
    # Link to patient (male partner)
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.PROTECT,
        related_name='sperm_analyses'
    )
    
    # Optional link to IVF cycle
    cycle = models.ForeignKey(
        IVFCycle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sperm_analyses'
    )
    
    # Sample Information
    collection_date = models.DateField(
        help_text="Date of sample collection"
    )
    
    collection_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Time of sample collection"
    )
    
    abstinence_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Days of abstinence before collection"
    )
    
    sample_source = models.CharField(
        max_length=20,
        choices=SampleSource.choices,
        default=SampleSource.FRESH_EJACULATE,
        help_text="Source of sperm sample"
    )
    
    # Macroscopic Parameters
    volume = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Volume (mL) - WHO ref: >= 1.4 mL"
    )
    
    appearance = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('NORMAL', 'Normal (Grey-opalescent)'),
            ('YELLOW', 'Yellow'),
            ('RED_BROWN', 'Red/Brown (Haemospermia)'),
            ('CLEAR', 'Clear'),
        ],
        help_text="Sample appearance"
    )
    
    liquefaction_time = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Liquefaction time (minutes) - Normal: < 60 min"
    )
    
    ph = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="pH - WHO ref: >= 7.2"
    )
    
    viscosity = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('NORMAL', 'Normal'),
            ('INCREASED', 'Increased'),
        ],
        help_text="Viscosity assessment"
    )
    
    # Microscopic Parameters (WHO 2021 reference values)
    concentration = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Sperm concentration (million/mL) - WHO ref: >= 16 million/mL"
    )
    
    total_sperm_count = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total sperm count (million) - WHO ref: >= 39 million"
    )
    
    # Motility (WHO 2021)
    progressive_motility = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Progressive motility (%) - WHO ref: >= 30%"
    )
    
    non_progressive_motility = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Non-progressive motility (%)"
    )
    
    immotile = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Immotile sperm (%)"
    )
    
    total_motility = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total motility (%) - WHO ref: >= 42%"
    )
    
    # Morphology (WHO 2021 strict criteria)
    normal_forms = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Normal morphology (%) - WHO ref: >= 4%"
    )
    
    head_defects = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Head defects (%)"
    )
    
    midpiece_defects = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Midpiece defects (%)"
    )
    
    tail_defects = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Tail defects (%)"
    )
    
    # Vitality
    vitality = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Vitality/Live sperm (%) - WHO ref: >= 54%"
    )
    
    # Other cells
    round_cells = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Round cells (million/mL)"
    )
    
    wbc_count = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="WBC count (million/mL) - Normal: < 1 million/mL"
    )
    
    # DNA Fragmentation (if performed)
    dna_fragmentation_index = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="DNA Fragmentation Index (DFI) %"
    )
    
    # Assessment
    assessment = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('NORMOZOOSPERMIA', 'Normozoospermia'),
            ('OLIGOZOOSPERMIA', 'Oligozoospermia'),
            ('ASTHENOZOOSPERMIA', 'Asthenozoospermia'),
            ('TERATOZOOSPERMIA', 'Teratozoospermia'),
            ('OLIGOASTHENOZOOSPERMIA', 'Oligoasthenozoospermia'),
            ('OLIGOASTHENOTERATOZOOSPERMIA', 'Oligoasthenoteratozoospermia (OAT)'),
            ('AZOOSPERMIA', 'Azoospermia'),
            ('CRYPTOZOOSPERMIA', 'Cryptozoospermia'),
            ('NECROZOOSPERMIA', 'Necrozoospermia'),
        ],
        help_text="Overall assessment"
    )
    
    recommendation = models.TextField(
        blank=True,
        help_text="Clinical recommendation"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Additional notes"
    )
    
    # Audit
    analyzed_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='sperm_analyses'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ivf_sperm_analysis'
        ordering = ['-collection_date']
        verbose_name = 'Sperm Analysis'
        verbose_name_plural = 'Sperm Analyses'
    
    def __str__(self):
        return f"Sperm Analysis - {self.patient} - {self.collection_date}"


class Embryo(models.Model):
    """
    Embryo Record
    
    Tracks individual embryos from fertilization through disposition.
    Nigerian Compliance: Chain of custody tracking required.
    """
    
    class Status(models.TextChoices):
        FERTILIZED = 'FERTILIZED', 'Fertilized (2PN)'
        CLEAVING = 'CLEAVING', 'Cleaving'
        MORULA = 'MORULA', 'Morula'
        BLASTOCYST = 'BLASTOCYST', 'Blastocyst'
        TRANSFERRED = 'TRANSFERRED', 'Transferred'
        FROZEN = 'FROZEN', 'Frozen (Cryopreserved)'
        THAWED = 'THAWED', 'Thawed'
        DISCARDED = 'DISCARDED', 'Discarded'
        DONATED = 'DONATED', 'Donated'
        ARRESTED = 'ARRESTED', 'Arrested Development'
    
    class FertilizationMethod(models.TextChoices):
        CONVENTIONAL_IVF = 'IVF', 'Conventional IVF'
        ICSI = 'ICSI', 'ICSI'
        SPLIT = 'SPLIT', 'Split (IVF + ICSI)'
        IMSI = 'IMSI', 'IMSI'
    
    cycle = models.ForeignKey(
        IVFCycle,
        on_delete=models.CASCADE,
        related_name='embryos'
    )
    
    # Identification
    embryo_number = models.PositiveIntegerField(
        help_text="Embryo number within the cycle"
    )
    
    # Unique identifier for tracking
    lab_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique laboratory identifier"
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.FERTILIZED,
        help_text="Current embryo status"
    )
    
    fertilization_method = models.CharField(
        max_length=20,
        choices=FertilizationMethod.choices,
        default=FertilizationMethod.CONVENTIONAL_IVF,
        help_text="Method of fertilization"
    )
    
    fertilization_date = models.DateField(
        help_text="Date of fertilization (Day 0)"
    )
    
    fertilization_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Time of insemination/ICSI"
    )
    
    # Day 1 Assessment (Fertilization check)
    day1_pn_status = models.CharField(
        max_length=15,
        blank=True,
        choices=[
            ('2PN', '2 Pronuclei (Normal)'),
            ('1PN', '1 Pronucleus'),
            ('3PN', '3 Pronuclei (Abnormal)'),
            ('0PN', 'No Pronuclei'),
            ('DEGENERATED', 'Degenerated'),
        ],
        help_text="Pronuclear status at Day 1"
    )
    
    # Day 2-3 Assessment (Cleavage stage)
    day2_cell_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Cell count at Day 2"
    )
    
    day3_cell_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Cell count at Day 3"
    )
    
    day3_grade = models.CharField(
        max_length=10,
        blank=True,
        help_text="Day 3 embryo grade (e.g., 8A, 6B)"
    )
    
    fragmentation = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Fragmentation percentage"
    )
    
    # Day 5-6 Assessment (Blastocyst)
    blastocyst_day = models.PositiveIntegerField(
        null=True,
        blank=True,
        choices=[(5, 'Day 5'), (6, 'Day 6'), (7, 'Day 7')],
        help_text="Day blastocyst formed"
    )
    
    blastocyst_grade = models.CharField(
        max_length=10,
        blank=True,
        help_text="Blastocyst grade (e.g., 4AA, 3BB)"
    )
    
    expansion_grade = models.CharField(
        max_length=5,
        blank=True,
        choices=[
            ('1', '1 - Early blastocyst'),
            ('2', '2 - Blastocyst'),
            ('3', '3 - Full blastocyst'),
            ('4', '4 - Expanded blastocyst'),
            ('5', '5 - Hatching blastocyst'),
            ('6', '6 - Hatched blastocyst'),
        ],
        help_text="Blastocyst expansion grade"
    )
    
    icm_grade = models.CharField(
        max_length=5,
        blank=True,
        choices=[
            ('A', 'A - Many cells, tightly packed'),
            ('B', 'B - Several cells, loosely grouped'),
            ('C', 'C - Few cells'),
        ],
        help_text="Inner Cell Mass (ICM) grade"
    )
    
    trophectoderm_grade = models.CharField(
        max_length=5,
        blank=True,
        choices=[
            ('A', 'A - Many cells, cohesive layer'),
            ('B', 'B - Few cells, loose epithelium'),
            ('C', 'C - Very few cells'),
        ],
        help_text="Trophectoderm (TE) grade"
    )
    
    # PGT (Preimplantation Genetic Testing)
    pgt_performed = models.BooleanField(
        default=False,
        help_text="PGT performed on this embryo"
    )
    
    pgt_result = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('EUPLOID', 'Euploid (Normal)'),
            ('ANEUPLOID', 'Aneuploid (Abnormal)'),
            ('MOSAIC', 'Mosaic'),
            ('NO_RESULT', 'No Result'),
            ('PENDING', 'Pending'),
        ],
        help_text="PGT result"
    )
    
    pgt_details = models.TextField(
        blank=True,
        help_text="Detailed PGT findings"
    )
    
    # Cryopreservation
    frozen_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date embryo was frozen"
    )
    
    storage_location = models.CharField(
        max_length=100,
        blank=True,
        help_text="Cryostorage tank/canister/position"
    )
    
    straw_id = models.CharField(
        max_length=50,
        blank=True,
        help_text="Cryostraw identifier"
    )
    
    thaw_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date embryo was thawed"
    )
    
    survived_thaw = models.BooleanField(
        null=True,
        blank=True,
        help_text="Did embryo survive thawing?"
    )
    
    # Disposition
    disposition = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('TRANSFERRED', 'Transferred'),
            ('STORAGE', 'In Storage'),
            ('DISCARDED_QUALITY', 'Discarded - Poor Quality'),
            ('DISCARDED_CONSENT', 'Discarded - Per Consent'),
            ('DISCARDED_EXPIRED', 'Discarded - Storage Expired'),
            ('DONATED_RESEARCH', 'Donated to Research'),
            ('DONATED_PATIENT', 'Donated to Another Patient'),
        ],
        help_text="Final embryo disposition"
    )
    
    disposition_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of disposition"
    )
    
    disposition_notes = models.TextField(
        blank=True,
        help_text="Notes on disposition"
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        help_text="Additional notes"
    )
    
    # Audit
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='embryos_created'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ivf_embryos'
        ordering = ['cycle', 'embryo_number']
        unique_together = [['cycle', 'embryo_number']]
        verbose_name = 'Embryo'
        verbose_name_plural = 'Embryos'
    
    def __str__(self):
        return f"Embryo #{self.embryo_number} ({self.lab_id}) - {self.status}"
    
    def save(self, *args, **kwargs):
        # Auto-generate lab_id if not set
        if not self.lab_id:
            date_str = self.fertilization_date.strftime('%Y%m%d')
            self.lab_id = f"EMB-{self.cycle_id}-{date_str}-{self.embryo_number:02d}"
        super().save(*args, **kwargs)


class EmbryoTransfer(models.Model):
    """
    Embryo Transfer Procedure
    
    Records the embryo transfer procedure and details.
    """
    
    class TransferType(models.TextChoices):
        FRESH = 'FRESH', 'Fresh Transfer'
        FROZEN = 'FROZEN', 'Frozen Embryo Transfer (FET)'
    
    class Difficulty(models.TextChoices):
        EASY = 'EASY', 'Easy'
        MODERATE = 'MODERATE', 'Moderate'
        DIFFICULT = 'DIFFICULT', 'Difficult'
    
    cycle = models.ForeignKey(
        IVFCycle,
        on_delete=models.CASCADE,
        related_name='embryo_transfers'
    )
    
    # Procedure Details
    transfer_date = models.DateField(
        help_text="Date of embryo transfer"
    )
    
    transfer_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Time of transfer"
    )
    
    transfer_type = models.CharField(
        max_length=20,
        choices=TransferType.choices,
        default=TransferType.FRESH,
        help_text="Type of transfer"
    )
    
    # Embryos transferred
    embryos = models.ManyToManyField(
        Embryo,
        related_name='transfers',
        help_text="Embryos transferred"
    )
    
    embryos_transferred_count = models.PositiveIntegerField(
        default=1,
        help_text="Number of embryos transferred"
    )
    
    embryo_stage = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('CLEAVAGE', 'Cleavage Stage (Day 2-3)'),
            ('BLASTOCYST', 'Blastocyst (Day 5-6)'),
        ],
        help_text="Stage of embryos transferred"
    )
    
    # Technique
    catheter_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Transfer catheter used"
    )
    
    ultrasound_guided = models.BooleanField(
        default=True,
        help_text="Transfer performed under ultrasound guidance"
    )
    
    difficulty = models.CharField(
        max_length=20,
        choices=Difficulty.choices,
        default=Difficulty.EASY,
        help_text="Technical difficulty"
    )
    
    # Uterine Position
    endometrial_thickness = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Endometrial thickness at transfer (mm)"
    )
    
    uterine_position = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('ANTEVERTED', 'Anteverted'),
            ('RETROVERTED', 'Retroverted'),
            ('MIDPOSITION', 'Mid-position'),
        ],
        help_text="Uterine position"
    )
    
    # Transfer Details
    distance_from_fundus = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Distance of catheter tip from fundus (cm)"
    )
    
    blood_on_catheter = models.BooleanField(
        default=False,
        help_text="Blood observed on catheter"
    )
    
    mucus_on_catheter = models.BooleanField(
        default=False,
        help_text="Mucus observed on catheter"
    )
    
    embryos_retained = models.BooleanField(
        default=False,
        help_text="Were any embryos retained in catheter?"
    )
    
    # Post-procedure
    bed_rest_duration = models.PositiveIntegerField(
        default=30,
        help_text="Recommended bed rest (minutes)"
    )
    
    medications_prescribed = models.JSONField(
        default=list,
        blank=True,
        help_text="Post-transfer medications"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Procedure notes"
    )
    
    # Performing doctor
    performed_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='embryo_transfers'
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ivf_embryo_transfers'
        ordering = ['-transfer_date']
        verbose_name = 'Embryo Transfer'
        verbose_name_plural = 'Embryo Transfers'
    
    def __str__(self):
        return f"Transfer {self.transfer_date} - {self.embryos_transferred_count} embryo(s)"


class IVFMedication(models.Model):
    """
    IVF Medication Prescription and Administration
    
    Tracks all medications used during IVF treatment.
    """
    
    class MedicationCategory(models.TextChoices):
        GnRH_AGONIST = 'GNRH_AGONIST', 'GnRH Agonist'
        GnRH_ANTAGONIST = 'GNRH_ANTAGONIST', 'GnRH Antagonist'
        GONADOTROPIN = 'GONADOTROPIN', 'Gonadotropin (FSH/LH)'
        HCG = 'HCG', 'hCG Trigger'
        PROGESTERONE = 'PROGESTERONE', 'Progesterone Support'
        ESTROGEN = 'ESTROGEN', 'Estrogen'
        ANTIBIOTIC = 'ANTIBIOTIC', 'Antibiotic'
        OTHER = 'OTHER', 'Other'
    
    cycle = models.ForeignKey(
        IVFCycle,
        on_delete=models.CASCADE,
        related_name='medications'
    )
    
    # Medication Details
    medication_name = models.CharField(
        max_length=100,
        help_text="Medication name"
    )
    
    category = models.CharField(
        max_length=20,
        choices=MedicationCategory.choices,
        help_text="Medication category"
    )
    
    dose = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Dose amount"
    )
    
    unit = models.CharField(
        max_length=20,
        help_text="Dose unit (e.g., IU, mg, mcg)"
    )
    
    route = models.CharField(
        max_length=30,
        choices=[
            ('SUBCUTANEOUS', 'Subcutaneous'),
            ('INTRAMUSCULAR', 'Intramuscular'),
            ('ORAL', 'Oral'),
            ('VAGINAL', 'Vaginal'),
            ('TRANSDERMAL', 'Transdermal'),
        ],
        help_text="Route of administration"
    )
    
    frequency = models.CharField(
        max_length=50,
        help_text="Frequency (e.g., Once daily, Twice daily)"
    )
    
    start_date = models.DateField(
        help_text="Start date"
    )
    
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="End date (if known)"
    )
    
    instructions = models.TextField(
        blank=True,
        help_text="Special instructions"
    )
    
    # Prescribing doctor
    prescribed_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='ivf_medications_prescribed'
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ivf_medications'
        ordering = ['cycle', 'start_date']
        verbose_name = 'IVF Medication'
        verbose_name_plural = 'IVF Medications'
    
    def __str__(self):
        return f"{self.medication_name} {self.dose}{self.unit}"


class IVFOutcome(models.Model):
    """
    IVF Pregnancy and Birth Outcome
    
    Tracks pregnancy progress and final outcome for successful cycles.
    """
    
    cycle = models.OneToOneField(
        IVFCycle,
        on_delete=models.CASCADE,
        related_name='outcome'
    )
    
    # Pregnancy Confirmation
    clinical_pregnancy = models.BooleanField(
        default=False,
        help_text="Clinical pregnancy confirmed (gestational sac on ultrasound)"
    )
    
    clinical_pregnancy_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date clinical pregnancy confirmed"
    )
    
    fetal_heartbeat = models.BooleanField(
        default=False,
        help_text="Fetal heartbeat detected"
    )
    
    fetal_heartbeat_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date fetal heartbeat detected"
    )
    
    # Multiple Pregnancy
    gestational_sacs = models.PositiveIntegerField(
        default=0,
        help_text="Number of gestational sacs"
    )
    
    fetal_poles = models.PositiveIntegerField(
        default=0,
        help_text="Number of fetal poles with heartbeat"
    )
    
    # Pregnancy Loss
    miscarriage = models.BooleanField(
        default=False,
        help_text="Miscarriage occurred"
    )
    
    miscarriage_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of miscarriage"
    )
    
    miscarriage_gestational_age = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Gestational age at miscarriage (weeks)"
    )
    
    ectopic = models.BooleanField(
        default=False,
        help_text="Ectopic pregnancy"
    )
    
    # Delivery
    delivery_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of delivery"
    )
    
    gestational_age_at_delivery = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Gestational age at delivery (weeks)"
    )
    
    delivery_type = models.CharField(
        max_length=30,
        blank=True,
        choices=[
            ('VAGINAL', 'Vaginal Delivery'),
            ('CESAREAN_ELECTIVE', 'Elective Cesarean Section'),
            ('CESAREAN_EMERGENCY', 'Emergency Cesarean Section'),
        ],
        help_text="Type of delivery"
    )
    
    # Birth Details
    live_births = models.PositiveIntegerField(
        default=0,
        help_text="Number of live births"
    )
    
    stillbirths = models.PositiveIntegerField(
        default=0,
        help_text="Number of stillbirths"
    )
    
    neonatal_deaths = models.PositiveIntegerField(
        default=0,
        help_text="Number of neonatal deaths"
    )
    
    # Birth weights (JSON array for multiples)
    birth_weights = models.JSONField(
        default=list,
        blank=True,
        help_text="Birth weights in grams [3200, 2800]"
    )
    
    # Complications
    maternal_complications = models.TextField(
        blank=True,
        help_text="Maternal complications during pregnancy/delivery"
    )
    
    neonatal_complications = models.TextField(
        blank=True,
        help_text="Neonatal complications"
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        help_text="Additional notes"
    )
    
    # Audit
    recorded_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='ivf_outcomes_recorded'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ivf_outcomes'
        verbose_name = 'IVF Outcome'
        verbose_name_plural = 'IVF Outcomes'
    
    def __str__(self):
        if self.live_births > 0:
            return f"Live Birth ({self.live_births}) - Cycle {self.cycle_id}"
        elif self.clinical_pregnancy:
            return f"Pregnant - Cycle {self.cycle_id}"
        else:
            return f"Outcome Pending - Cycle {self.cycle_id}"


class IVFConsent(models.Model):
    """
    IVF Consent Documentation
    
    Nigerian Legal Requirement: All IVF procedures require documented consent.
    Tracks all consent forms and their status.
    """
    
    class ConsentType(models.TextChoices):
        TREATMENT = 'TREATMENT', 'IVF Treatment Consent'
        EGG_RETRIEVAL = 'EGG_RETRIEVAL', 'Egg Retrieval Consent'
        SPERM_COLLECTION = 'SPERM_COLLECTION', 'Sperm Collection Consent'
        EMBRYO_TRANSFER = 'EMBRYO_TRANSFER', 'Embryo Transfer Consent'
        EMBRYO_FREEZING = 'EMBRYO_FREEZING', 'Embryo Cryopreservation Consent'
        EMBRYO_DISPOSITION = 'EMBRYO_DISPOSITION', 'Embryo Disposition Consent'
        EGG_FREEZING = 'EGG_FREEZING', 'Egg Freezing Consent'
        SPERM_FREEZING = 'SPERM_FREEZING', 'Sperm Freezing Consent'
        PGT = 'PGT', 'Genetic Testing Consent'
        DONOR_EGG = 'DONOR_EGG', 'Donor Egg Consent'
        DONOR_SPERM = 'DONOR_SPERM', 'Donor Sperm Consent'
        SURROGACY = 'SURROGACY', 'Surrogacy Agreement Consent'
    
    cycle = models.ForeignKey(
        IVFCycle,
        on_delete=models.CASCADE,
        related_name='consents'
    )
    
    consent_type = models.CharField(
        max_length=30,
        choices=ConsentType.choices,
        help_text="Type of consent"
    )
    
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.PROTECT,
        related_name='ivf_consents'
    )
    
    # Consent Status
    signed = models.BooleanField(
        default=False,
        help_text="Has been signed"
    )
    
    signed_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date signed"
    )
    
    signed_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Time signed"
    )
    
    # Witness Information
    witness_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Witness name"
    )
    
    witness_signature = models.BooleanField(
        default=False,
        help_text="Witness signed"
    )
    
    # Document Reference
    document_path = models.FileField(
        upload_to='ivf_consents/',
        null=True,
        blank=True,
        help_text="Scanned consent document"
    )
    
    # Revocation
    revoked = models.BooleanField(
        default=False,
        help_text="Consent has been revoked"
    )
    
    revoked_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date consent was revoked"
    )
    
    revocation_reason = models.TextField(
        blank=True,
        help_text="Reason for revocation"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Additional notes"
    )
    
    # Audit
    recorded_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='ivf_consents_recorded'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ivf_consents'
        ordering = ['-created_at']
        unique_together = [['cycle', 'consent_type', 'patient']]
        verbose_name = 'IVF Consent'
        verbose_name_plural = 'IVF Consents'
    
    def __str__(self):
        status = "Signed" if self.signed else "Pending"
        return f"{self.get_consent_type_display()} - {status}"

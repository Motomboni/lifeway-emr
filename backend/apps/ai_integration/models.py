"""
AI Integration models for EMR system.

Per EMR Rules:
- All AI interactions are visit-scoped
- Audit logging for compliance
- Cost tracking and rate limiting
"""
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal

User = get_user_model()


class AIProvider(models.TextChoices):
    """Supported AI providers."""
    OPENAI = 'openai', 'OpenAI'
    ANTHROPIC = 'anthropic', 'Anthropic'
    LOCAL = 'local', 'Local Model'
    AZURE_OPENAI = 'azure_openai', 'Azure OpenAI'


class AIFeatureType(models.TextChoices):
    """Available AI feature types."""
    CLINICAL_DECISION_SUPPORT = 'clinical_decision_support', 'Clinical Decision Support'
    NLP_SUMMARIZATION = 'nlp_summarization', 'NLP Summarization'
    NLP_EXTRACTION = 'nlp_extraction', 'NLP Extraction'
    AUTOMATED_CODING = 'automated_coding', 'Automated Coding (ICD-11/CPT)'
    DRUG_INTERACTION_CHECK = 'drug_interaction_check', 'Drug Interaction Check'
    DIAGNOSIS_SUGGESTION = 'diagnosis_suggestion', 'Diagnosis Suggestion'
    DOCUMENTATION_ASSISTANCE = 'documentation_assistance', 'Documentation Assistance'
    IMAGE_ANALYSIS = 'image_analysis', 'Image Analysis'
    CLINICAL_NOTE_GENERATION = 'clinical_note_generation', 'Clinical Note Generation'


class AIRequest(models.Model):
    """
    Tracks all AI API requests for audit and cost tracking.
    
    Per EMR Rules:
    - Visit-scoped (all requests tied to a visit)
    - Immutable (append-only for compliance)
    - Audit trail for all AI interactions
    """
    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.PROTECT,
        related_name='ai_requests',
        help_text="Visit this AI request is associated with"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='ai_requests',
        help_text="User who initiated the AI request"
    )
    user_role = models.CharField(
        max_length=50,
        help_text="Role of the user at time of request"
    )
    feature_type = models.CharField(
        max_length=50,
        choices=AIFeatureType.choices,
        help_text="Type of AI feature used"
    )
    provider = models.CharField(
        max_length=50,
        choices=AIProvider.choices,
        help_text="AI provider used"
    )
    model_name = models.CharField(
        max_length=200,
        help_text="Specific model used (e.g., 'gpt-4', 'claude-3-opus')"
    )
    prompt_tokens = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Number of tokens in the prompt"
    )
    completion_tokens = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Number of tokens in the completion"
    )
    total_tokens = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Total tokens used"
    )
    cost_usd = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=Decimal('0.000000'),
        validators=[MinValueValidator(Decimal('0.000000'))],
        help_text="Cost in USD for this request"
    )
    request_payload = models.JSONField(
        default=dict,
        blank=True,
        help_text="Request payload (sanitized, no PHI)"
    )
    response_payload = models.JSONField(
        default=dict,
        blank=True,
        help_text="Response payload (sanitized, no PHI)"
    )
    success = models.BooleanField(
        default=True,
        help_text="Whether the request was successful"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if request failed"
    )
    response_time_ms = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Response time in milliseconds"
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="When the request was made"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the request"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata"
    )

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['visit', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['feature_type', '-timestamp']),
            models.Index(fields=['provider', '-timestamp']),
        ]

    def __str__(self):
        return f"AI Request {self.id} - {self.feature_type} - {self.visit_id}"


class AIConfiguration(models.Model):
    """
    Configuration for AI providers and features.
    
    Allows per-feature configuration of AI providers and models.
    """
    feature_type = models.CharField(
        max_length=50,
        choices=AIFeatureType.choices,
        unique=True,
        help_text="AI feature type"
    )
    default_provider = models.CharField(
        max_length=50,
        choices=AIProvider.choices,
        help_text="Default provider for this feature"
    )
    default_model = models.CharField(
        max_length=200,
        help_text="Default model for this feature"
    )
    enabled = models.BooleanField(
        default=True,
        help_text="Whether this feature is enabled"
    )
    max_tokens = models.IntegerField(
        default=4000,
        validators=[MinValueValidator(1)],
        help_text="Maximum tokens for requests"
    )
    temperature = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('0.7'),
        validators=[MinValueValidator(Decimal('0.0')), MinValueValidator(Decimal('2.0'))],
        help_text="Temperature for AI responses (0.0-2.0)"
    )
    rate_limit_per_minute = models.IntegerField(
        default=60,
        validators=[MinValueValidator(1)],
        help_text="Rate limit per minute per user"
    )
    cost_per_1k_tokens = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=Decimal('0.000000'),
        help_text="Cost per 1k tokens (for cost tracking)"
    )
    configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional provider-specific configuration"
    )
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "AI Configuration"
        verbose_name_plural = "AI Configurations"

    def __str__(self):
        return f"{self.get_feature_type_display()} - {self.default_provider}"


class AICache(models.Model):
    """
    Cache for AI responses to reduce API calls and costs.
    
    Caches responses based on prompt hash and feature type.
    """
    feature_type = models.CharField(
        max_length=50,
        choices=AIFeatureType.choices,
        db_index=True
    )
    prompt_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text="SHA-256 hash of the prompt"
    )
    response = models.JSONField(
        help_text="Cached AI response"
    )
    expires_at = models.DateTimeField(
        db_index=True,
        help_text="When this cache entry expires"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    hit_count = models.IntegerField(
        default=0,
        help_text="Number of times this cache was hit"
    )

    class Meta:
        unique_together = [['feature_type', 'prompt_hash']]
        indexes = [
            models.Index(fields=['feature_type', 'prompt_hash']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"AI Cache - {self.feature_type} - {self.prompt_hash[:8]}"


class ClinicalNote(models.Model):
    """
    AI-generated clinical notes. Doctor must approve/edit before final save.
    """
    NOTE_TYPE_CHOICES = [
        ('SOAP', 'SOAP'),
        ('summary', 'Summary'),
        ('discharge', 'Discharge'),
    ]
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='clinical_notes',
        help_text="Patient this note is for",
    )
    doctor = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='clinical_notes_authored',
        help_text="Doctor who created/approved the note",
    )
    appointment = models.ForeignKey(
        'appointments.Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clinical_notes',
        help_text="Related appointment if applicable",
    )
    note_type = models.CharField(
        max_length=20,
        choices=NOTE_TYPE_CHOICES,
        help_text="Type of note (SOAP, summary, discharge)",
    )
    raw_transcript = models.TextField(
        blank=True,
        help_text="Original transcript or bullet notes used for generation",
    )
    ai_generated_note = models.TextField(
        blank=True,
        help_text="AI-generated structured note",
    )
    doctor_edited_note = models.TextField(
        blank=True,
        help_text="Final note after doctor edit/approval",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'clinical_notes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient']),
            models.Index(fields=['doctor']),
            models.Index(fields=['appointment']),
            models.Index(fields=['note_type']),
        ]
        verbose_name = 'Clinical Note'
        verbose_name_plural = 'Clinical Notes'

    def __str__(self):
        return f"ClinicalNote {self.id} - {self.note_type} - patient {self.patient_id}"

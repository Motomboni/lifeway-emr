"""
Procedure Task models - nurse-executed procedures.

Per EMR Rules:
- Procedures are consultation-dependent
- Procedures are visit-scoped
- Procedures are executed by nurses
- Procedures require consultation context
"""
from django.db import models
from django.core.exceptions import ValidationError


class ProcedureTask(models.Model):
    """
    Procedure Task model - nurse-executed procedures.
    
    Design Principles:
    1. Consultation-dependent: Must have a consultation
    2. Visit-scoped: Must belong to a visit
    3. Nurse-executed: Executed by nurses
    4. ServiceCatalog-driven: Created from ServiceCatalog selection
    """
    
    class Status(models.TextChoices):
        ORDERED = "ORDERED", "Ordered"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
    
    # Core relationships
    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.PROTECT,
        related_name='procedure_tasks',
        help_text="Visit this procedure belongs to. Procedures are visit-scoped."
    )
    
    consultation = models.ForeignKey(
        'consultations.Consultation',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='procedure_tasks',
        help_text="Consultation this procedure belongs to. Required for clinical procedures, optional for registration/administrative services."
    )
    
    service_catalog = models.ForeignKey(
        'billing.ServiceCatalog',
        on_delete=models.PROTECT,
        related_name='procedure_tasks',
        help_text="ServiceCatalog service that generated this procedure task"
    )
    
    ordered_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='procedure_tasks_ordered',
        help_text="Doctor who ordered the procedure. PROTECT prevents deletion."
    )
    
    executed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='procedure_tasks_executed',
        help_text="Nurse who executed the procedure"
    )
    
    # Procedure details
    procedure_name = models.CharField(
        max_length=255,
        help_text="Name of the procedure (snapshot from ServiceCatalog)"
    )
    
    procedure_description = models.TextField(
        blank=True,
        help_text="Description of the procedure"
    )
    
    clinical_indication = models.TextField(
        blank=True,
        help_text="Clinical reason for performing the procedure"
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ORDERED,
        help_text="Status of the procedure task"
    )
    
    # Execution details
    execution_notes = models.TextField(
        blank=True,
        help_text="Notes from the nurse executing the procedure"
    )
    
    execution_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the procedure was executed"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the procedure task was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the procedure task was last updated"
    )
    
    class Meta:
        db_table = 'procedure_tasks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['visit']),
            models.Index(fields=['consultation']),
            models.Index(fields=['service_catalog']),
            models.Index(fields=['status']),
            models.Index(fields=['ordered_by']),
            models.Index(fields=['executed_by']),
        ]
        verbose_name = 'Procedure Task'
        verbose_name_plural = 'Procedure Tasks'
    
    def __str__(self):
        return f"Procedure Task {self.id}: {self.procedure_name} for Visit {self.visit_id}"
    
    def clean(self):
        """
        Validation: Ensure procedure task can be created.
        
        Rules:
        1. Visit must be OPEN (not CLOSED)
        2. Consultation must belong to same visit
        3. Consultation must be ACTIVE or CLOSED (not PENDING)
        4. ServiceCatalog must be active
        5. ServiceCatalog workflow_type must be PROCEDURE
        """
        if not self.visit_id:
            return
        
        visit = self.visit
        
        # ❌ Closed visit immutability
        if visit.status == 'CLOSED':
            raise ValidationError("Cannot create ProcedureTask on a closed visit.")
        
        # ❌ Consultation must belong to same visit (if consultation is provided)
        if self.consultation_id and self.visit_id:
            if self.consultation.visit_id != self.visit_id:
                raise ValidationError("Consultation does not belong to this Visit.")
            
            # ❌ Consultation must be ACTIVE or CLOSED (not PENDING)
            if self.consultation.status == 'PENDING':
                raise ValidationError(
                    "Cannot create ProcedureTask for a PENDING consultation. "
                    "Consultation must be ACTIVE or CLOSED."
                )
        
        # ❌ ServiceCatalog validation
        if self.service_catalog_id:
            service = self.service_catalog
            if not service.is_active:
                raise ValidationError(f"ServiceCatalog '{service.service_code}' is not active.")
            
            if service.workflow_type != 'PROCEDURE':
                raise ValidationError(
                    f"ServiceCatalog '{service.service_code}' is not a PROCEDURE service. "
                    f"Workflow type: {service.workflow_type}"
                )
            
            # Check if this is a registration service (doesn't require consultation)
            is_registration = (
                (service.service_code or '').upper().startswith('REG-') or
                'REGISTRATION' in (service.name or '').upper() or
                'REGISTRATION' in (service.description or '').upper()
            )
            
            # Registration services don't require consultation
            if not is_registration and not service.requires_consultation:
                raise ValidationError(
                    f"PROCEDURE service '{service.service_code}' must require consultation "
                    f"(unless it's a registration service)."
                )
            
            # Non-registration procedures must have consultation
            if not is_registration and not self.consultation_id:
                raise ValidationError(
                    f"PROCEDURE service '{service.service_code}' requires a consultation "
                    f"(unless it's a registration service)."
                )
    
    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def execute(self, nurse, execution_notes: str = '') -> None:
        """
        Execute the procedure (nurse action).
        
        Args:
            nurse: User (nurse) executing the procedure
            execution_notes: Notes from execution
        """
        if nurse.role != 'NURSE':
            raise ValidationError("Only nurses can execute procedures.")
        
        if self.status == 'COMPLETED':
            raise ValidationError("Procedure is already completed.")
        
        if self.status == 'CANCELLED':
            raise ValidationError("Cannot execute a cancelled procedure.")
        
        from django.utils import timezone
        
        self.executed_by = nurse
        self.status = 'COMPLETED'
        self.execution_notes = execution_notes
        self.execution_date = timezone.now()
        self.save()


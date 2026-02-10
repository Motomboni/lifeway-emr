"""
ServiceCatalog model for Service-Driven EMR system.

Per EMR Rules:
- Services drive workflows, not just pricing
- ServiceCatalog does NOT store patient-specific data
- Each service defines what workflow it triggers
- Services are billable and workflow-triggering
"""
from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal


class ServiceCatalog(models.Model):
    """
    ServiceCatalog model - Represents billable and workflow-triggering services.
    
    This model defines services that:
    1. Can be billed to patients
    2. Trigger specific workflows in the EMR
    3. Have role-based access control
    4. Define billing behavior (auto-bill, timing)
    
    Design Principles:
    - NO patient/visit/consultation foreign keys (service definitions only)
    - Services drive workflows, not just pricing
    - Each service defines what workflow it triggers
    - Role-based access control via allowed_roles
    """
    
    DEPARTMENT_CHOICES = [
        ('CONSULTATION', 'Consultation'),
        ('LAB', 'Laboratory'),
        ('PHARMACY', 'Pharmacy'),
        ('RADIOLOGY', 'Radiology'),
        ('PROCEDURE', 'Procedure'),
    ]
    
    CATEGORY_CHOICES = [
        ('CONSULTATION', 'Consultation'),
        ('LAB', 'Laboratory Test'),
        ('DRUG', 'Drug/Medication'),
        ('PROCEDURE', 'Procedure'),
        ('RADIOLOGY', 'Radiology Study'),
    ]
    
    WORKFLOW_TYPE_CHOICES = [
        ('GOPD_CONSULT', 'GOPD Consultation'),
        ('LAB_ORDER', 'Laboratory Order'),
        ('DRUG_DISPENSE', 'Drug Dispensing'),
        ('PROCEDURE', 'Procedure'),
        ('RADIOLOGY_STUDY', 'Radiology Study'),
        ('IVF', 'IVF'),
        ('INJECTION', 'Injection'),
        ('DRESSING', 'Dressing'),
        ('VACCINATION', 'Vaccination'),
        ('PHYSIOTHERAPY', 'Physiotherapy'),
        ('OTHER', 'Other'),
    ]
    
    BILL_TIMING_CHOICES = [
        ('BEFORE', 'Before Service'),
        ('AFTER', 'After Service'),
    ]
    
    # Basic Information
    department = models.CharField(
        max_length=50,
        choices=DEPARTMENT_CHOICES,
        db_index=True,
        help_text="Department that provides this service"
    )
    
    service_code = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Unique, human-readable service code (e.g., 'CONS-001', 'CBC-001')"
    )
    
    name = models.CharField(
        max_length=255,
        help_text="Service name (e.g., 'General Consultation', 'Complete Blood Count')"
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Service price/amount"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the service"
    )
    
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        help_text="Service category"
    )
    
    # Workflow Configuration
    workflow_type = models.CharField(
        max_length=50,
        choices=WORKFLOW_TYPE_CHOICES,
        help_text="Type of workflow this service triggers"
    )
    
    requires_visit = models.BooleanField(
        default=True,
        help_text="Whether this service requires an active visit"
    )
    
    requires_consultation = models.BooleanField(
        default=False,
        help_text="Whether this service requires a consultation"
    )
    
    # Billing Configuration
    auto_bill = models.BooleanField(
        default=True,
        help_text="Whether to automatically create a bill when service is ordered"
    )
    
    bill_timing = models.CharField(
        max_length=10,
        choices=BILL_TIMING_CHOICES,
        default='AFTER',
        help_text="When to bill for this service (BEFORE or AFTER service delivery)"
    )
    
    # Pre-service payment gate (strict payment rules)
    # True = payment required BEFORE access (Registration, Doctor Consultation only)
    # False = billed after consultation; payment collected by Reception only
    restricted_service_flag = models.BooleanField(
        default=False,
        db_index=True,
        help_text="If True, payment must be collected before access (Registration & Consultation only). "
                  "All other services are post-consultation, reception-only payment."
    )
    
    # Access Control
    allowed_roles = models.JSONField(
        default=list,
        help_text="List of user roles allowed to order this service (e.g., ['DOCTOR', 'NURSE'])"
    )
    
    # Auto-assignment (for workflows like GOPD_CONSULT)
    auto_assign_doctor = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='auto_assigned_services',
        help_text="Doctor to auto-assign when this service is selected (optional). Only applies to consultation workflows."
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this service is currently active/available"
    )
    
    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this service was added to catalog"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this service was last updated"
    )
    
    class Meta:
        db_table = 'service_catalog'
        verbose_name = 'Service Catalog'
        verbose_name_plural = 'Service Catalog'
        ordering = ['department', 'service_code']
        indexes = [
            models.Index(fields=['service_code']),
            models.Index(fields=['department']),
            models.Index(fields=['department', 'is_active']),
            models.Index(fields=['workflow_type']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.service_code} - {self.name} ({self.department})"
    
    def clean(self):
        """Validate service catalog entry."""
        errors = {}
        
        # Validate amount
        if self.amount <= 0:
            errors['amount'] = "Service amount must be greater than zero."
        
        # Validate service_code
        if not self.service_code or not self.service_code.strip():
            errors['service_code'] = "Service code is required."
        
        # Validate name
        if not self.name or not self.name.strip():
            errors['name'] = "Service name is required."
        
        # Validate department and category consistency
        department_category_map = {
            'CONSULTATION': ['CONSULTATION'],
            'LAB': ['LAB'],
            'PHARMACY': ['DRUG'],
            'RADIOLOGY': ['RADIOLOGY'],
            'PROCEDURE': ['PROCEDURE'],
        }
        
        valid_categories = department_category_map.get(self.department, [])
        if valid_categories and self.category not in valid_categories:
            errors['category'] = (
                f"Category '{self.category}' is not valid for department '{self.department}'. "
                f"Valid categories: {', '.join(valid_categories)}"
            )
        
        # Validate workflow_type and department consistency
        department_workflow_map = {
            'CONSULTATION': ['GOPD_CONSULT', 'IVF', 'OTHER'],
            'LAB': ['LAB_ORDER', 'OTHER'],
            'PHARMACY': ['DRUG_DISPENSE', 'OTHER'],
            'RADIOLOGY': ['RADIOLOGY_STUDY', 'OTHER'],
            'PROCEDURE': ['PROCEDURE', 'INJECTION', 'DRESSING', 'VACCINATION', 'PHYSIOTHERAPY', 'IVF', 'OTHER'],
        }
        
        valid_workflows = department_workflow_map.get(self.department, ['OTHER'])
        if self.workflow_type not in valid_workflows:
            errors['workflow_type'] = (
                f"Workflow type '{self.workflow_type}' is not valid for department '{self.department}'. "
                f"Valid workflow types: {', '.join(valid_workflows)}"
            )
        
        # Validate requires_consultation logic
        if self.requires_consultation and not self.requires_visit:
            errors['requires_consultation'] = (
                "A service that requires consultation must also require a visit."
            )
        
        # Validate allowed_roles
        if not isinstance(self.allowed_roles, list):
            errors['allowed_roles'] = "allowed_roles must be a list."
        elif len(self.allowed_roles) == 0:
            errors['allowed_roles'] = "At least one role must be allowed to order this service."
        else:
            valid_roles = ['ADMIN', 'DOCTOR', 'NURSE', 'LAB_TECH', 'RADIOLOGY_TECH', 
                          'PHARMACIST', 'RECEPTIONIST', 'PATIENT']
            invalid_roles = [role for role in self.allowed_roles if role not in valid_roles]
            if invalid_roles:
                errors['allowed_roles'] = (
                    f"Invalid roles: {', '.join(invalid_roles)}. "
                    f"Valid roles: {', '.join(valid_roles)}"
                )
        
        # Validate bill_timing
        if self.bill_timing not in dict(self.BILL_TIMING_CHOICES):
            errors['bill_timing'] = f"Invalid bill_timing. Must be one of: {', '.join([c[0] for c in self.BILL_TIMING_CHOICES])}"
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def is_registration_service(self) -> bool:
        """True if this service is Patient Registration (pre-service payment required)."""
        return (
            self.service_code.upper().startswith('REG-') or
            'REGISTRATION' in (self.name or '').upper() or
            (self.description or '').upper().find('REGISTRATION') >= 0
        )
    
    def is_consultation_service(self) -> bool:
        """True if this service is Doctor Consultation (pre-service payment required)."""
        return (
            self.workflow_type == 'GOPD_CONSULT' or
            self.department == 'CONSULTATION' or
            self.service_code.upper().startswith('CONS-') or
            'CONSULTATION' in (self.name or '').upper() or
            'CONSULT' in (self.name or '').upper()
        )
    
    def requires_payment_before_access(self) -> bool:
        """True if payment must be collected before granting access (Registration or Consultation)."""
        return self.restricted_service_flag
    
    def can_be_ordered_by(self, user_role: str) -> bool:
        """
        Check if a user with the given role can order this service.
        
        Args:
            user_role: User's role (e.g., 'DOCTOR', 'NURSE', 'RECEPTIONIST')
        
        Returns:
            bool: True if user can order this service
        
        Special Rules:
        - Receptionists can always order registration services (service_code starts with 'REG-' or name contains 'REGISTRATION')
        - Receptionists can always order consultation services (GOPD_CONSULT workflow type)
        - Other services follow allowed_roles strictly
        """
        # Special case: Receptionists can handle all registration services
        if user_role == 'RECEPTIONIST':
            is_registration = (
                self.service_code.upper().startswith('REG-') or
                'REGISTRATION' in self.name.upper() or
                'REGISTRATION' in (self.description or '').upper()
            )
            if is_registration:
                return True
            
            # Receptionists can order consultation services
            # Check by workflow_type, department, service_code pattern, or name
            is_consultation = (
                self.workflow_type == 'GOPD_CONSULT' or
                self.department == 'CONSULTATION' or
                self.service_code.upper().startswith('CONS-') or
                'FOLLOW UP' in self.name.upper() or
                'FOLLOW-UP' in self.name.upper() or
                'FOLLOWUP' in self.name.upper() or
                'CONSULTATION' in self.name.upper() or
                'CONSULT' in self.name.upper()
            )
            if is_consultation:
                return True
        
        # For all other cases, check allowed_roles
        return user_role in self.allowed_roles
    
    def get_workflow_config(self) -> dict:
        """
        Get workflow configuration for this service.
        
        Returns:
            dict with workflow configuration
        """
        return {
            'workflow_type': self.workflow_type,
            'requires_visit': self.requires_visit,
            'requires_consultation': self.requires_consultation,
            'auto_bill': self.auto_bill,
            'bill_timing': self.bill_timing,
        }


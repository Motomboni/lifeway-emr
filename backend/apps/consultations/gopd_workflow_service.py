"""
GOPD Consultation Workflow Service - ServiceCatalog-driven orchestration.

Per EMR Rules:
- GOPD Consultation workflow is driven entirely by ServiceCatalog
- When service with workflow_type = GOPD_CONSULT is selected:
  - Create Visit (if none exists)
  - Create Consultation ONLY after payment if bill_timing = BEFORE
  - Lock doctor access until payment is confirmed
  - Auto-assign doctor if configured, otherwise leave unassigned
- Consultation status flow: PENDING → ACTIVE → CLOSED
"""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from typing import Optional, Tuple

from .models import Consultation
from apps.visits.models import Visit
from apps.visits.service_catalog_service import get_or_create_visit_for_service
from apps.billing.service_catalog_models import ServiceCatalog
from apps.patients.models import Patient
from apps.users.models import User


def initiate_gopd_consultation_workflow(
    patient: Patient,
    service: ServiceCatalog,
    user: Optional[User] = None,
    payment_type: str = 'CASH',
    chief_complaint: Optional[str] = None,
) -> Tuple[Visit, Optional[Consultation], bool]:
    """
    Initiate GOPD Consultation workflow from ServiceCatalog.
    
    This function orchestrates the complete GOPD consultation workflow:
    1. Validates service is GOPD_CONSULT
    2. Creates/gets Visit
    3. Creates Consultation if payment not required before, or marks as PENDING
    4. Auto-assigns doctor if configured
    5. Enforces payment guards
    
    Args:
        patient: Patient instance
        service: ServiceCatalog instance (must have workflow_type='GOPD_CONSULT')
        user: User initiating the workflow (optional, for audit)
        payment_type: Payment type ('CASH' or 'INSURANCE'), default 'CASH'
        chief_complaint: Chief complaint for the visit (optional)
    
    Returns:
        Tuple of (Visit, Consultation, consultation_created) where:
        - Visit: The visit (existing or newly created)
        - Consultation: The consultation if created, None if pending payment
        - consultation_created: True if consultation was created, False if pending
    
    Raises:
        ValidationError: If service is not GOPD_CONSULT or validation fails
    """
    # Validate service is GOPD_CONSULT
    if service.workflow_type != 'GOPD_CONSULT':
        raise ValidationError(
            f"This workflow is only for GOPD_CONSULT services. "
            f"Service '{service.service_code}' has workflow_type '{service.workflow_type}'."
        )
    
    if not service.is_active:
        raise ValidationError(f"Service '{service.service_code}' is not active.")
    
    # Use transaction to ensure atomicity
    with transaction.atomic():
        # Step 1: Create or get Visit
        visit, visit_created = get_or_create_visit_for_service(
            patient=patient,
            service=service,
            user=user,
            payment_type=payment_type,
            chief_complaint=chief_complaint,
        )
        
        # Step 2: Check if consultation already exists
        existing_consultation = Consultation.objects.filter(visit=visit).first()
        if existing_consultation:
            return visit, existing_consultation, False
        
        # Step 3: Determine if consultation should be created now
        # If bill_timing = BEFORE, payment must be cleared first
        # If bill_timing = AFTER, consultation can be created immediately
        
        consultation_created = False
        consultation = None
        
        if service.bill_timing == 'BEFORE':
            # Payment required before consultation
            # Check if payment is cleared
            if visit.is_payment_cleared():
                # Payment cleared - create consultation
                consultation = _create_consultation_for_visit(
                    visit=visit,
                    service=service,
                    assigned_doctor=service.auto_assign_doctor,
                )
                consultation_created = True
            else:
                # Payment not cleared - consultation remains PENDING (not created yet)
                # Consultation will be created when payment is confirmed
                consultation = None
        else:
            # bill_timing = AFTER - consultation can be created immediately
            consultation = _create_consultation_for_visit(
                visit=visit,
                service=service,
                assigned_doctor=service.auto_assign_doctor,
            )
            consultation_created = True
        
        return visit, consultation, consultation_created


def create_consultation_after_payment(
    visit: Visit,
    service: Optional[ServiceCatalog] = None,
    assigned_doctor: Optional[User] = None,
) -> Consultation:
    """
    Create consultation after payment is confirmed.
    
    This function is called when payment is confirmed for a visit
    that requires payment before consultation (bill_timing = BEFORE).
    
    Args:
        visit: Visit instance
        service: ServiceCatalog instance (optional, for auto-assignment)
        assigned_doctor: Doctor to assign (optional, overrides service.auto_assign_doctor)
    
    Returns:
        Consultation instance
    
    Raises:
        ValidationError: If consultation already exists or visit is invalid
    """
    # Check if consultation already exists
    existing_consultation = Consultation.objects.filter(visit=visit).first()
    if existing_consultation:
        # Update status to ACTIVE if it was PENDING
        if existing_consultation.status == 'PENDING':
            existing_consultation.status = 'ACTIVE'
            existing_consultation.save()
        return existing_consultation
    
    # Determine assigned doctor
    doctor = assigned_doctor
    if not doctor and service and service.auto_assign_doctor:
        doctor = service.auto_assign_doctor
    
    # Create consultation
    consultation = _create_consultation_for_visit(
        visit=visit,
        service=service,
        assigned_doctor=doctor,
    )
    
    return consultation


def _create_consultation_for_visit(
    visit: Visit,
    service: Optional[ServiceCatalog] = None,
    assigned_doctor: Optional[User] = None,
) -> Consultation:
    """
    Internal helper to create consultation for a visit.
    
    Args:
        visit: Visit instance
        service: ServiceCatalog instance (optional)
        assigned_doctor: Doctor to assign (optional)
    
    Returns:
        Consultation instance
    
    Raises:
        ValidationError: If visit is invalid or consultation cannot be created
    """
    # Validate visit
    if visit.status == 'CLOSED':
        raise ValidationError("Cannot create consultation for a CLOSED visit.")
    
    # Check if consultation already exists
    if Consultation.objects.filter(visit=visit).exists():
        raise ValidationError("Consultation already exists for this visit.")
    
    # Determine initial status
    # If payment is cleared, status is ACTIVE, otherwise PENDING
    initial_status = 'ACTIVE' if visit.is_payment_cleared() else 'PENDING'
    
    # Determine assigned doctor
    doctor = assigned_doctor
    if not doctor and service and service.auto_assign_doctor:
        doctor = service.auto_assign_doctor
    
    # Validate doctor if provided
    if doctor and doctor.role != 'DOCTOR':
        raise ValidationError(f"User '{doctor.username}' is not a doctor. Only doctors can be assigned to consultations.")
    
    # Create consultation
    consultation = Consultation.objects.create(
        visit=visit,
        created_by=doctor,  # Can be None if not auto-assigned
        status=initial_status,
    )
    
    return consultation


def can_doctor_access_consultation(consultation: Consultation, doctor: User) -> bool:
    """
    Check if a doctor can access a consultation.
    
    Rules:
    - If consultation has no assigned doctor (created_by is None), any doctor can access
    - If consultation has assigned doctor, only that doctor can access
    - Consultation must be in ACTIVE status (not PENDING or CLOSED)
    - Payment must be cleared for PENDING consultations
    
    Args:
        consultation: Consultation instance
        doctor: User instance (must be a doctor)
    
    Returns:
        bool: True if doctor can access consultation
    """
    # Validate doctor role
    if doctor.role != 'DOCTOR':
        return False
    
    # Check consultation status
    if consultation.status == 'CLOSED':
        return False  # Closed consultations are read-only
    
    # If consultation is PENDING, check payment
    if consultation.status == 'PENDING':
        if not consultation.visit.is_payment_cleared():
            return False  # Payment not cleared, doctor cannot access
    
    # Check doctor assignment
    if consultation.created_by is None:
        # No doctor assigned - any doctor can access
        return True
    
    # Doctor assigned - only assigned doctor can access
    return consultation.created_by == doctor


def activate_consultation(consultation: Consultation, doctor: User) -> Consultation:
    """
    Activate a consultation (change status from PENDING to ACTIVE).
    
    This function is called when:
    - Payment is confirmed for a PENDING consultation
    - Doctor is assigned to a PENDING consultation
    
    Args:
        consultation: Consultation instance
        doctor: User instance (must be a doctor)
    
    Returns:
        Consultation instance (updated)
    
    Raises:
        ValidationError: If consultation cannot be activated
    """
    # Validate doctor role
    if doctor.role != 'DOCTOR':
        raise ValidationError(f"User '{doctor.username}' is not a doctor.")
    
    # Validate consultation status
    if consultation.status != 'PENDING':
        raise ValidationError(
            f"Cannot activate consultation with status '{consultation.status}'. "
            "Only PENDING consultations can be activated."
        )
    
    # Check payment if bill_timing = BEFORE
    # (This check is done at the service level, but we validate here too)
    if not consultation.visit.is_payment_cleared():
        raise ValidationError(
            "Payment must be cleared before activating consultation. "
            f"Current payment status: {consultation.visit.payment_status}"
        )
    
    # Assign doctor if not already assigned
    if consultation.created_by is None:
        consultation.created_by = doctor
    
    # Activate consultation
    consultation.status = 'ACTIVE'
    consultation.save()
    
    return consultation


def close_consultation(consultation: Consultation, doctor: User) -> Consultation:
    """
    Close a consultation (change status from ACTIVE to CLOSED).
    
    Args:
        consultation: Consultation instance
        doctor: User instance (must be a doctor and must be assigned to consultation)
    
    Returns:
        Consultation instance (updated)
    
    Raises:
        ValidationError: If consultation cannot be closed
    """
    # Validate doctor role
    if doctor.role != 'DOCTOR':
        raise ValidationError(f"User '{doctor.username}' is not a doctor.")
    
    # Validate consultation status
    if consultation.status != 'ACTIVE':
        raise ValidationError(
            f"Cannot close consultation with status '{consultation.status}'. "
            "Only ACTIVE consultations can be closed."
        )
    
    # Validate doctor assignment
    if consultation.created_by and consultation.created_by != doctor:
        raise ValidationError(
            "Only the assigned doctor can close this consultation."
        )
    
    # Close consultation
    consultation.status = 'CLOSED'
    consultation.save()
    
    return consultation


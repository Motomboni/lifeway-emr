"""
Downstream Service Workflow Orchestration.

Per EMR Rules:
- LAB services: require_visit=true, require_consultation=true, doctor-only
- PHARMACY services: require_consultation=true, dispensed after billing
- PROCEDURES: nurse-executed, consultation-dependent

This module orchestrates the creation of domain objects when services are selected:
- LabOrder for LAB services
- Prescription for PHARMACY services
- ProcedureTask for PROCEDURES services

All services auto-generate billing (BillingLineItem).
"""
from django.db import transaction
from django.core.exceptions import ValidationError
from typing import Optional, Tuple, Dict, Any
from decimal import Decimal

from .models import Visit
from apps.billing.service_catalog_models import ServiceCatalog
from apps.billing.billing_line_item_service import create_billing_line_item_from_service
from apps.consultations.models import Consultation
from apps.laboratory.models import LabOrder
from apps.pharmacy.models import Prescription
from apps.clinical.procedure_models import ProcedureTask
from apps.radiology.models import RadiologyRequest
from apps.patients.models import Patient
from apps.users.models import User
from apps.core.compliance_checker import (
    validate_service_catalog_origin,
    validate_visit_consultation_chain,
)


def is_registration_service(service: ServiceCatalog) -> bool:
    """
    Check if a service is a registration service.
    
    Registration services are identified by:
    - Service code starting with 'REG-'
    - Service name containing 'REGISTRATION'
    - Description containing 'REGISTRATION'
    
    Registration services are administrative/billing services that don't require consultation.
    """
    service_code = (service.service_code or '').upper()
    service_name = (service.name or '').upper()
    description = (service.description or '').upper()
    
    return (
        service_code.startswith('REG-') or
        'REGISTRATION' in service_name or
        'REGISTRATION' in description
    )


def order_downstream_service(
    service: ServiceCatalog,
    visit: Visit,
    consultation: Optional[Consultation] = None,
    user: Optional[User] = None,
    additional_data: Optional[Dict[str, Any]] = None,
) -> Tuple[Any, Any]:
    """
    Order a downstream service (LAB, PHARMACY, PROCEDURES, RADIOLOGY).
    
    Per EMR Context Document v2 (LOCKED):
    - All clinical actions MUST originate from ServiceCatalog
    - Service-Driven, Visit-Scoped, Consultation-Dependent
    
    This function:
    1. Validates service requirements (visit, consultation, role)
    2. Creates the appropriate domain object (LabOrder, Prescription, ProcedureTask, RadiologyRequest)
    3. Auto-generates billing (BillingLineItem)
    4. Returns both the domain object and billing line item
    
    Args:
        service: ServiceCatalog instance (REQUIRED - all actions must originate from ServiceCatalog)
        visit: Visit instance
        consultation: Consultation instance (required for consultation-dependent services)
        user: User ordering the service (for role validation and audit)
        additional_data: Additional data for domain object creation (e.g., tests_requested, drug details)
    
    Returns:
        Tuple of (domain_object, billing_line_item)
        - domain_object: LabOrder, Prescription, ProcedureTask, or RadiologyRequest
        - billing_line_item: BillingLineItem created for the service
    
    Raises:
        ValidationError: If validation fails or service cannot be ordered
    """
    # ❌ GOVERNANCE RULE: All actions MUST originate from ServiceCatalog
    # Per EMR Context Document v2: "All clinical and operational actions MUST originate from a ServiceCatalog entry."
    validate_service_catalog_origin(
        action_type=f"Service ordering ({service.workflow_type})",
        service_catalog_id=service.id
    )
    
    # Validate service
    if not service.is_active:
        raise ValidationError(
            f"Service '{service.service_code}' is not active. "
            "Per EMR Context Document v2, only active services can be ordered."
        )
    
    # Validate user role
    if user and not service.can_be_ordered_by(user.role):
        raise ValidationError(
            f"User with role '{user.role}' cannot order service '{service.service_code}'. "
            f"Allowed roles: {service.allowed_roles}. "
            "Per EMR Context Document v2, role-based access is strictly enforced."
        )
    
    # Validate visit
    if visit.status != 'OPEN':
        raise ValidationError(
            f"Cannot order service on a closed visit. Visit {visit.id} is {visit.status}. "
            "Per EMR Context Document v2, all clinical actions are visit-scoped and require an OPEN visit."
        )
    
    # ❌ GOVERNANCE RULE: Validate Visit → Consultation chain
    # Per EMR Context Document v2: "No Consultation → No Lab / Radiology / Drug / Procedure Orders"
    # Exception: Registration services don't require consultation (administrative/billing services)
    if service.requires_consultation and not is_registration_service(service):
        validate_visit_consultation_chain(
            visit=visit,
            consultation=consultation,
            action_type=f"Service ordering ({service.workflow_type})"
        )
        
        # Validate consultation is not PENDING — except allow DOCTOR to order (auto-activate)
        if consultation and consultation.status == 'PENDING':
            if user and getattr(user, 'role', None) == 'DOCTOR':
                consultation.status = 'ACTIVE'
                if not consultation.created_by:
                    consultation.created_by = user
                consultation.save(update_fields=['status', 'created_by'])
            else:
                raise ValidationError(
                    f"Cannot order service '{service.service_code}' for a PENDING consultation. "
                    f"Consultation must be ACTIVE or CLOSED. "
                    "Per EMR Context Document v2, downstream services require an active consultation."
                )
    
    # Route to appropriate handler based on workflow_type
    workflow_type = service.workflow_type
    
    # For registration services, consultation can be None
    if is_registration_service(service):
        consultation = None
    
    if workflow_type == 'LAB_ORDER':
        return _order_lab_service(service, visit, consultation, user, additional_data)
    elif workflow_type == 'DRUG_DISPENSE':
        return _order_pharmacy_service(service, visit, consultation, user, additional_data)
    elif workflow_type == 'PROCEDURE':
        return _order_procedure_service(service, visit, consultation, user, additional_data)
    elif workflow_type == 'RADIOLOGY_STUDY' or service.department == 'RADIOLOGY':
        return _order_radiology_service(service, visit, consultation, user, additional_data)
    else:
        raise ValidationError(
            f"Service '{service.service_code}' has workflow_type '{workflow_type}' "
            f"which is not a downstream service. Use appropriate workflow for this service type."
        )


def _order_lab_service(
    service: ServiceCatalog,
    visit: Visit,
    consultation: Consultation,
    user: Optional[User],
    additional_data: Optional[Dict[str, Any]],
) -> Tuple[LabOrder, Any]:
    """
    Order a LAB service.
    
    Rules:
    - require_visit = true
    - require_consultation = true
    - ordered ONLY by doctor
    - Auto-creates LabOrder
    - Auto-generates billing
    
    Args:
        service: ServiceCatalog instance (LAB_ORDER workflow_type)
        visit: Visit instance
        consultation: Consultation instance (required)
        user: User ordering (must be DOCTOR)
        additional_data: Dict with 'tests_requested' (list) and optional 'clinical_indication' (str)
    
    Returns:
        Tuple of (LabOrder, BillingLineItem)
    """
    # Validate service is LAB_ORDER
    if service.workflow_type != 'LAB_ORDER':
        raise ValidationError(
            f"Service '{service.service_code}' is not a LAB_ORDER service. "
            f"Workflow type: {service.workflow_type}"
        )
    
    # Validate service requirements
    if not service.requires_visit:
        raise ValidationError(
            f"LAB service '{service.service_code}' must have requires_visit=true."
        )
    
    if not service.requires_consultation:
        raise ValidationError(
            f"LAB service '{service.service_code}' must have requires_consultation=true."
        )
    
    # Validate user is doctor
    if user and user.role != 'DOCTOR':
        raise ValidationError(
            f"Only doctors can order LAB services. User role: {user.role}"
        )
    
    # Extract additional data
    tests_requested = additional_data.get('tests_requested', []) if additional_data else []
    clinical_indication = additional_data.get('clinical_indication', '') if additional_data else ''
    
    if not tests_requested:
        raise ValidationError("LAB service requires 'tests_requested' in additional_data.")
    
    with transaction.atomic():
        # Create LabOrder
        lab_order = LabOrder.objects.create(
            visit=visit,
            consultation=consultation,
            ordered_by=user,
            tests_requested=tests_requested,
            clinical_indication=clinical_indication,
            status=LabOrder.Status.ORDERED,
        )
        
        # Auto-generate billing
        # Note: Consultation is NOT linked in BillingLineItem for downstream services
        # It's only tracked in the domain object (LabOrder)
        billing_line_item = create_billing_line_item_from_service(
            service=service,
            visit=visit,
            consultation=None,  # ❌ Per BillingLineItem validation: consultation only for GOPD_CONSULT
            created_by=user,
        )
        
        return lab_order, billing_line_item


def _order_pharmacy_service(
    service: ServiceCatalog,
    visit: Visit,
    consultation: Consultation,
    user: Optional[User],
    additional_data: Optional[Dict[str, Any]],
) -> Tuple[Prescription, Any]:
    """
    Order a PHARMACY service.
    
    Rules:
    - require_consultation = true
    - dispensed ONLY after billing
    - Auto-creates Prescription
    - Auto-generates billing
    
    Args:
        service: ServiceCatalog instance (DRUG_DISPENSE workflow_type)
        visit: Visit instance
        consultation: Consultation instance (required)
        user: User ordering (typically DOCTOR)
        additional_data: Dict with 'drug' (Drug instance), 'dosage', 'frequency', 'duration', etc.
    
    Returns:
        Tuple of (Prescription, BillingLineItem)
    """
    # Validate service is DRUG_DISPENSE
    if service.workflow_type != 'DRUG_DISPENSE':
        raise ValidationError(
            f"Service '{service.service_code}' is not a DRUG_DISPENSE service. "
            f"Workflow type: {service.workflow_type}"
        )
    
    # Validate service requirements
    if not service.requires_consultation:
        raise ValidationError(
            f"PHARMACY service '{service.service_code}' must have requires_consultation=true."
        )
    
    # Extract additional data - auto-populate from service catalog if not provided
    if not additional_data:
        additional_data = {}
    
    # Use service name as drug name if not explicitly provided
    drug_name = additional_data.get('drug') or additional_data.get('drug_name') or service.name
    if not drug_name:
        raise ValidationError("PHARMACY service requires 'drug' or 'drug_name' in additional_data, or service must have a name.")
    
    drug_code = additional_data.get('drug_code', service.service_code)
    dosage = additional_data.get('dosage', 'As prescribed')  # Default value
    frequency = additional_data.get('frequency', 'As directed')  # Default value
    duration = additional_data.get('duration', 'As needed')  # Default value
    instructions = additional_data.get('instructions', 'Take as directed by physician')
    quantity = additional_data.get('quantity', '')
    
    with transaction.atomic():
        # Create Prescription
        prescription = Prescription.objects.create(
            visit=visit,
            consultation=consultation,
            drug=drug_name,  # Prescription uses CharField for drug name
            drug_code=drug_code,
            prescribed_by=user,
            dosage=dosage,
            frequency=frequency,
            duration=duration,
            instructions=instructions,
            quantity=quantity,
            status='PENDING',  # Prescription uses 'PENDING', 'DISPENSED', 'CANCELLED'
        )
        
        # Auto-generate billing
        # Note: Consultation is NOT linked in BillingLineItem for downstream services
        # It's only tracked in the domain object (Prescription)
        billing_line_item = create_billing_line_item_from_service(
            service=service,
            visit=visit,
            consultation=None,  # ❌ Per BillingLineItem validation: consultation only for GOPD_CONSULT
            created_by=user,
        )
        
        return prescription, billing_line_item


def _order_procedure_service(
    service: ServiceCatalog,
    visit: Visit,
    consultation: Consultation,
    user: Optional[User],
    additional_data: Optional[Dict[str, Any]],
) -> Tuple[ProcedureTask, Any]:
    """
    Order a PROCEDURE service.
    
    Rules:
    - nurse-executed
    - consultation-dependent
    - Auto-creates ProcedureTask
    - Auto-generates billing
    
    Args:
        service: ServiceCatalog instance (PROCEDURE workflow_type)
        visit: Visit instance
        consultation: Consultation instance (required)
        user: User ordering (typically DOCTOR)
        additional_data: Dict with optional 'clinical_indication' (str)
    
    Returns:
        Tuple of (ProcedureTask, BillingLineItem)
    """
    # Validate service is PROCEDURE
    if service.workflow_type != 'PROCEDURE':
        raise ValidationError(
            f"Service '{service.service_code}' is not a PROCEDURE service. "
            f"Workflow type: {service.workflow_type}"
        )
    
    # Validate service requirements
    # Registration services don't require consultation (administrative/billing services)
    is_registration = is_registration_service(service)
    
    if not is_registration and not service.requires_consultation:
        raise ValidationError(
            f"PROCEDURE service '{service.service_code}' must have requires_consultation=true "
            f"(unless it's a registration service)."
        )
    
    # Registration services don't require consultation - ensure None is passed
    if is_registration:
        consultation = None  # Explicitly set to None for registration services
    
    # Extract additional data
    clinical_indication = additional_data.get('clinical_indication', '') if additional_data else ''
    
    with transaction.atomic():
        # Create ProcedureTask
        # Registration services can have consultation=None
        procedure_task = ProcedureTask.objects.create(
            visit=visit,
            consultation=consultation,  # Can be None for registration services
            service_catalog=service,
            ordered_by=user,
            procedure_name=service.name,
            procedure_description=service.description or '',
            clinical_indication=clinical_indication,
            status=ProcedureTask.Status.ORDERED,
        )
        
        # Auto-generate billing
        # Note: Consultation is NOT linked in BillingLineItem for downstream services
        # It's only tracked in the domain object (ProcedureTask)
        billing_line_item = create_billing_line_item_from_service(
            service=service,
            visit=visit,
            consultation=None,  # ❌ Per BillingLineItem validation: consultation only for GOPD_CONSULT
            created_by=user,
        )
        
        return procedure_task, billing_line_item


def _order_radiology_service(
    service: ServiceCatalog,
    visit: Visit,
    consultation: Consultation,
    user: Optional[User],
    additional_data: Optional[Dict[str, Any]],
) -> Tuple[RadiologyRequest, Any]:
    """
    Order a RADIOLOGY service.
    
    Rules:
    - require_visit = true
    - require_consultation = true
    - ordered ONLY by doctor
    - Auto-creates RadiologyRequest
    - Auto-generates billing
    
    Args:
        service: ServiceCatalog instance (RADIOLOGY_STUDY workflow_type)
        visit: Visit instance
        consultation: Consultation instance (required)
        user: User ordering (must be DOCTOR)
        additional_data: Dict with optional 'study_type', 'study_code', 'clinical_indication', 'instructions'
    
    Returns:
        Tuple of (RadiologyRequest, BillingLineItem)
    """
    # Accept RADIOLOGY_STUDY workflow or any service in RADIOLOGY department (e.g. workflow_type OTHER)
    if service.workflow_type != 'RADIOLOGY_STUDY' and service.department != 'RADIOLOGY':
        raise ValidationError(
            f"Service '{service.service_code}' is not a radiology service. "
            f"Workflow type: {service.workflow_type}, department: {service.department}"
        )
    
    # Validate service requirements
    if not service.requires_visit:
        raise ValidationError(
            f"RADIOLOGY service '{service.service_code}' must have requires_visit=true."
        )
    
    if not service.requires_consultation:
        raise ValidationError(
            f"RADIOLOGY service '{service.service_code}' must have requires_consultation=true."
        )
    
    # Validate user is doctor
    if user and user.role != 'DOCTOR':
        raise ValidationError(
            f"Only doctors can order RADIOLOGY services. User role: {user.role}"
        )
    
    # Extract additional data
    study_type = additional_data.get('study_type', service.name) if additional_data else service.name
    study_code = additional_data.get('study_code', service.service_code) if additional_data else service.service_code
    clinical_indication = additional_data.get('clinical_indication', '') if additional_data else ''
    instructions = additional_data.get('instructions', '') if additional_data else ''
    film_size = additional_data.get('film_size', '') if additional_data else ''
    patient_location = additional_data.get('patient_location', '') if additional_data else ''
    view_type = additional_data.get('view_type', '') if additional_data else ''
    
    # study_type defaults to service name if not provided
    if not study_type:
        study_type = 'General Study'
    
    image_metadata = {}
    if film_size and film_size.strip():
        image_metadata['film_size'] = film_size.strip()
    if patient_location and patient_location.strip():
        image_metadata['patient_location'] = patient_location.strip()
    if view_type and view_type.strip():
        image_metadata['view_type'] = view_type.strip()
    
    with transaction.atomic():
        # Create RadiologyRequest
        radiology_request = RadiologyRequest.objects.create(
            visit=visit,
            consultation=consultation,
            ordered_by=user,
            study_type=study_type,
            study_code=study_code,
            clinical_indication=clinical_indication,
            instructions=instructions,
            status='PENDING',
            image_metadata=image_metadata if image_metadata else {},
        )
        
        # Auto-generate billing
        # Note: Consultation is NOT linked in BillingLineItem for downstream services
        # It's only tracked in the domain object (RadiologyRequest)
        billing_line_item = create_billing_line_item_from_service(
            service=service,
            visit=visit,
            consultation=None,  # ❌ Per BillingLineItem validation: consultation only for GOPD_CONSULT
            created_by=user,
        )
        
        return radiology_request, billing_line_item


def can_dispense_prescription(prescription: Prescription) -> bool:
    """
    Check if a prescription can be dispensed.
    
    Rules:
    - Prescription must be PENDING
    - Billing must be PAID (dispensed ONLY after billing)
    
    Args:
        prescription: Prescription instance
    
    Returns:
        bool: True if prescription can be dispensed
    """
    if prescription.status != 'PENDING':
        return False
    
    # Check if billing is paid
    from apps.billing.billing_line_item_models import BillingLineItem
    
    # Find billing line item for this prescription's consultation
    billing_line_item = BillingLineItem.objects.filter(
        visit=prescription.visit,
        consultation=prescription.consultation,
        service_catalog__workflow_type='DRUG_DISPENSE',
    ).first()
    
    if not billing_line_item:
        return False
    
    return billing_line_item.bill_status == 'PAID'


"""
Prescription Dispensing Service.

Per Nigerian Clinic Operational Realities:
- Standard: Payment must be cleared before dispensing
- Emergency: Can override with proper authorization
- Clear audit trail for emergency dispensing
"""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Prescription
from apps.core.validators import validate_prescription_dispensing


def dispense_prescription(
    prescription: Prescription,
    pharmacist,
    emergency_override: bool = False,
    dispensing_notes: str = '',
) -> Prescription:
    """
    Dispense a prescription.
    
    Nigerian Clinic Governance Rules:
    - Standard: Billing must be PAID before dispensing
    - Emergency: Can override with is_emergency flag and proper authorization
    
    Args:
        prescription: Prescription instance to dispense
        pharmacist: User (must be PHARMACIST role)
        emergency_override: Boolean flag for emergency override
        dispensing_notes: Notes from pharmacist
    
    Returns:
        Updated Prescription instance
    
    Raises:
        ValidationError: If validation fails
    """
    # Validate pharmacist role
    if pharmacist.role != 'PHARMACIST':
        raise ValidationError(
            "Only pharmacists can dispense prescriptions. "
            "User role '%(role)s' is not authorized."
        ) % {'role': pharmacist.role}
    
    # Validate prescription can be dispensed
    validate_prescription_dispensing(
        prescription,
        emergency_override=emergency_override or prescription.is_emergency
    )
    
    with transaction.atomic():
        # Update prescription
        prescription.status = 'DISPENSED'
        prescription.dispensed = True
        prescription.dispensed_by = pharmacist
        prescription.dispensed_date = timezone.now()
        prescription.dispensing_notes = dispensing_notes
        
        # If emergency override, ensure flag is set
        if emergency_override:
            prescription.is_emergency = True
        
        prescription.save()
        
        return prescription


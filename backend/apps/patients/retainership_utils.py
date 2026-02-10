"""
Retainership Utilities - Check retainership status and apply discounts.

Per EMR Rules:
- Retainership must be active (has_retainership=True)
- Retainership must not be expired (if end_date exists, must be in future)
- Retainership discounts apply to all charges
- Retainership type determines discount percentage
"""
from datetime import date
from decimal import Decimal
from typing import Dict, Any, Optional
from django.core.exceptions import ValidationError

from .models import Patient


# Retainership discount percentages by type
RETAINERSHIP_DISCOUNTS = {
    'MONTHLY': Decimal('10.00'),  # 10% discount
    'QUARTERLY': Decimal('15.00'),  # 15% discount
    'ANNUAL': Decimal('20.00'),  # 20% discount
    'CORPORATE': Decimal('25.00'),  # 25% discount
    # Default discount for other types
    'DEFAULT': Decimal('10.00'),  # 10% default discount
}


def is_retainership_active(patient: Patient, check_date: Optional[date] = None) -> bool:
    """
    Check if patient has an active retainership.
    
    Args:
        patient: Patient instance
        check_date: Date to check against (defaults to today)
    
    Returns:
        bool: True if retainership is active, False otherwise
    
    Conditions for active retainership:
    1. has_retainership must be True
    2. retainership_start_date must exist and be <= check_date
    3. If retainership_end_date exists, it must be >= check_date
    """
    if not patient.has_retainership:
        return False
    
    if not patient.retainership_start_date:
        return False
    
    if check_date is None:
        check_date = date.today()
    
    # Check if start date has passed
    if patient.retainership_start_date > check_date:
        return False
    
    # Check if end date exists and has passed
    if patient.retainership_end_date and patient.retainership_end_date < check_date:
        return False
    
    return True


def get_retainership_discount_percentage(patient: Patient) -> Decimal:
    """
    Get discount percentage for patient's retainership type.
    
    Args:
        patient: Patient instance
    
    Returns:
        Decimal: Discount percentage (e.g., 10.00 for 10%)
    
    Returns 0 if patient doesn't have active retainership.
    """
    if not is_retainership_active(patient):
        return Decimal('0.00')
    
    if not patient.retainership_type:
        return RETAINERSHIP_DISCOUNTS['DEFAULT']
    
    # Normalize retainership type to uppercase
    retainership_type = patient.retainership_type.upper().strip()
    
    # Check if type exists in discounts dict
    if retainership_type in RETAINERSHIP_DISCOUNTS:
        return RETAINERSHIP_DISCOUNTS[retainership_type]
    
    # Return default discount for unknown types
    return RETAINERSHIP_DISCOUNTS['DEFAULT']


def compute_retainership_discount(total_charges: Decimal, patient: Patient) -> Decimal:
    """
    Compute retainership discount amount.
    
    Args:
        total_charges: Total charges before discount
        patient: Patient instance
    
    Returns:
        Decimal: Discount amount
    
    Example:
        total_charges = 1000.00
        discount_percentage = 10.00 (10%)
        discount_amount = 100.00
    """
    if not is_retainership_active(patient):
        return Decimal('0.00')
    
    discount_percentage = get_retainership_discount_percentage(patient)
    
    if discount_percentage == 0:
        return Decimal('0.00')
    
    # Calculate discount: total_charges * (discount_percentage / 100)
    discount_amount = (total_charges * discount_percentage) / Decimal('100.00')
    
    # Round to 2 decimal places
    return discount_amount.quantize(Decimal('0.01'))


def get_retainership_info(patient: Patient) -> Dict[str, Any]:
    """
    Get comprehensive retainership information for a patient.
    
    Args:
        patient: Patient instance
    
    Returns:
        dict with:
            - has_retainership: bool
            - is_active: bool
            - retainership_type: str or None
            - retainership_start_date: date or None
            - retainership_end_date: date or None
            - retainership_amount: Decimal or None
            - discount_percentage: Decimal
            - days_until_expiry: int or None (negative if expired)
            - is_expired: bool
    """
    has_retainership = patient.has_retainership
    is_active = is_retainership_active(patient)
    discount_percentage = get_retainership_discount_percentage(patient)
    
    # Calculate days until expiry
    days_until_expiry = None
    is_expired = False
    
    if patient.retainership_end_date:
        today = date.today()
        days_until_expiry = (patient.retainership_end_date - today).days
        is_expired = days_until_expiry < 0
    
    return {
        'has_retainership': has_retainership,
        'is_active': is_active,
        'retainership_type': patient.retainership_type,
        'retainership_start_date': patient.retainership_start_date,
        'retainership_end_date': patient.retainership_end_date,
        'retainership_amount': patient.retainership_amount,
        'discount_percentage': discount_percentage,
        'days_until_expiry': days_until_expiry,
        'is_expired': is_expired,
    }


def validate_retainership_dates(patient: Patient) -> None:
    """
    Validate retainership dates.
    
    Raises ValidationError if dates are invalid.
    
    Validations:
    - If has_retainership is True, retainership_start_date must exist
    - If retainership_end_date exists, it must be >= retainership_start_date
    """
    if not patient.has_retainership:
        return
    
    if not patient.retainership_start_date:
        raise ValidationError(
            "Retainership start date is required when patient has retainership."
        )
    
    if patient.retainership_end_date:
        if patient.retainership_end_date < patient.retainership_start_date:
            raise ValidationError(
                "Retainership end date must be after start date."
            )


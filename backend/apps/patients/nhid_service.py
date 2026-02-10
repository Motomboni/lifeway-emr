"""
National Health ID verification (Nigeria-ready stub).

verify_national_health_id(id_number, name, dob) -> valid: bool, message: str
Stub: simulate NIN/NHIA validation; in production integrate with official API.
"""
import logging
from typing import Tuple
from django.utils import timezone

logger = logging.getLogger(__name__)


def verify_national_health_id(
    id_number: str,
    name: str,
    dob,
) -> Tuple[bool, str]:
    """
    Stub: verify National Health ID against external source (NIN/NHIA).

    Args:
        id_number: National Health ID number.
        name: Full name to match.
        dob: Date of birth (date object or string).

    Returns:
        (valid: bool, message: str)
    """
    id_number = (id_number or "").strip()
    name = (name or "").strip()
    if not id_number:
        return False, "ID number is required."
    if not name:
        return False, "Name is required."
    # Stub: accept if ID looks like 11 digits (NIN style) or alphanumeric
    if len(id_number) < 8:
        return False, "Invalid ID format."
    # Simulate success for stub (production: call NIN/NHIA API)
    logger.info("NHID verify stub: id=%s name=%s dob=%s", id_number[:4] + "***", name[:3] + "***", dob)
    return True, "Verification successful (stub)."

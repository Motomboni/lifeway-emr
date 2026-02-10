"""
Billing Signals - Charge creation for clinical actions.

Per product requirement: No item is added automatically.
Charges are created only when:
- A service is added from the Service Catalog (BillingLineItem via add-item API), or
- A manual MISC charge is added by the receptionist.

Automatic charge creation for Consultation, Lab, Radiology, and Prescription is DISABLED
to prevent duplication and to ensure charges come only from the catalog or manual entry.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal

from apps.consultations.models import Consultation
from apps.laboratory.models import LabOrder
from apps.radiology.models import RadiologyOrder
from apps.pharmacy.models import Prescription


# Default charge amounts (can be overridden in settings) - used only if auto-creation is re-enabled
DEFAULT_CONSULTATION_FEE = Decimal('5000.00')  # ₦5,000
DEFAULT_LAB_FEE = Decimal('3000.00')  # ₦3,000
DEFAULT_RADIOLOGY_FEE = Decimal('4000.00')  # ₦4,000
DEFAULT_DRUG_FEE = Decimal('2500.00')  # ₦2,500


# ---------------------------------------------------------------------------
# AUTO-ADD DISABLED: Consultation Fee is only added when selected from catalog.
# ---------------------------------------------------------------------------
@receiver(post_save, sender=Consultation)
def create_consultation_charge(sender, instance, created, **kwargs):
    """
    No longer creates a consultation charge automatically.
    Consultation fee is added only when the user adds it from the Service Catalog.
    """
    if not created or not instance.visit:
        return
    # No-op: charges are added only from Service Catalog or manual MISC.


# ---------------------------------------------------------------------------
# AUTO-ADD DISABLED: Lab charge is only added when selected from catalog.
# ---------------------------------------------------------------------------
@receiver(post_save, sender=LabOrder)
def create_lab_charge(sender, instance, created, **kwargs):
    """
    No longer creates a lab charge automatically.
    Lab charges are added only when the user adds the service from the Service Catalog.
    """
    if not created or not instance.visit:
        return
    # No-op: charges are added only from Service Catalog or manual MISC.


# ---------------------------------------------------------------------------
# AUTO-ADD DISABLED: Radiology charge is only added when selected from catalog.
# ---------------------------------------------------------------------------
@receiver(post_save, sender=RadiologyOrder)
def create_radiology_charge(sender, instance, created, **kwargs):
    """
    No longer creates a radiology charge automatically.
    Radiology charges are added only when the user adds the service from the Service Catalog.
    """
    if not created or not instance.visit:
        return
    # No-op: charges are added only from Service Catalog or manual MISC.


# ---------------------------------------------------------------------------
# AUTO-ADD DISABLED: Drug charge is only added when selected from catalog.
# ---------------------------------------------------------------------------
@receiver(post_save, sender=Prescription)
def create_prescription_charge(sender, instance, created, **kwargs):
    """
    No longer creates a drug charge automatically.
    Drug charges are added only when the user adds the service from the Service Catalog.
    """
    if not created or not instance.visit:
        return
    # No-op: charges are added only from Service Catalog or manual MISC.


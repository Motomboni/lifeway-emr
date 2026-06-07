"""
Visit signals - e.g. set organization from patient.
"""

from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import Visit


@receiver(pre_save, sender=Visit)
def set_visit_organization(sender, instance, **kwargs):
    """Set Visit.organization from Patient.organization if not set."""
    if instance.patient_id and not instance.organization_id:
        instance.organization_id = instance.patient.organization_id

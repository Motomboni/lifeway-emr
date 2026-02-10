"""
Signals for wallet app.

Auto-creates wallet when patient is created.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.patients.models import Patient
from .models import Wallet


@receiver(post_save, sender=Patient)
def create_patient_wallet(sender, instance, created, **kwargs):
    """
    Auto-create wallet when a patient is created.
    """
    if created:
        Wallet.objects.create(
            patient=instance,
            balance=0.00,
            currency='NGN',
            is_active=True
        )

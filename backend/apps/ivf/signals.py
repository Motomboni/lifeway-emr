"""
IVF Module Signals

Handles automatic actions and integrations for IVF events.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import IVFCycle, OocyteRetrieval, EmbryoTransfer, Embryo


@receiver(post_save, sender=IVFCycle)
def handle_cycle_status_change(sender, instance, created, **kwargs):
    """
    Handle IVF cycle status changes.
    
    - Trigger notifications
    - Update related records
    - Create audit trail
    """
    if created:
        # New cycle created - could trigger notifications
        pass
    else:
        # Status change handling
        if instance.status == IVFCycle.Status.COMPLETED:
            # Cycle completed - trigger outcome tracking reminder
            pass
        elif instance.status == IVFCycle.Status.CANCELLED:
            # Cycle cancelled - update related records
            pass


@receiver(post_save, sender=OocyteRetrieval)
def handle_oocyte_retrieval(sender, instance, created, **kwargs):
    """
    Handle oocyte retrieval completion.
    
    - Update cycle status to RETRIEVAL
    - Trigger lab notification
    """
    if created:
        cycle = instance.cycle
        if cycle.status == IVFCycle.Status.STIMULATION:
            cycle.status = IVFCycle.Status.RETRIEVAL
            cycle.save(update_fields=['status'])


@receiver(post_save, sender=EmbryoTransfer)
def handle_embryo_transfer(sender, instance, created, **kwargs):
    """
    Handle embryo transfer completion.
    
    - Update cycle status to TRANSFER
    - Mark embryos as transferred
    """
    if created:
        cycle = instance.cycle
        
        # Update cycle status
        cycle.status = IVFCycle.Status.TRANSFER
        cycle.save(update_fields=['status'])
        
        # Update embryo statuses (already done in view, but backup here)
        instance.embryos.update(status=Embryo.Status.TRANSFERRED)


@receiver(pre_save, sender=Embryo)
def generate_embryo_lab_id(sender, instance, **kwargs):
    """
    Generate unique lab ID for embryos before save.
    """
    if not instance.lab_id and instance.fertilization_date:
        date_str = instance.fertilization_date.strftime('%Y%m%d')
        
        # Get next embryo number in cycle if not set
        if not instance.embryo_number:
            existing_count = Embryo.objects.filter(cycle=instance.cycle).count()
            instance.embryo_number = existing_count + 1
        
        instance.lab_id = f"EMB-{instance.cycle_id}-{date_str}-{instance.embryo_number:02d}"

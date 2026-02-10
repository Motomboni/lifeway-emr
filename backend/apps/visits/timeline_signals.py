"""
Django signals for auto-logging timeline events.

This module automatically creates timeline events when significant
actions occur in the EMR system.
"""
import logging
import threading
from django.db.models.signals import post_save, post_init
from django.dispatch import receiver
from django.utils import timezone

from .timeline_models import TimelineEvent
from .models import Visit
from apps.consultations.models import Consultation

# Thread-local storage to prevent recursion in post_init signals
_thread_local = threading.local()
from apps.laboratory.models import LabOrder, LabResult
from apps.radiology.models import RadiologyRequest
from apps.pharmacy.models import Prescription
from apps.billing.billing_line_item_models import BillingLineItem
from apps.clinical.procedure_models import ProcedureTask

logger = logging.getLogger(__name__)


def create_timeline_event(
    visit,
    event_type,
    description,
    actor=None,
    source_type=None,
    source_id=None,
    metadata=None,
    timestamp=None
):
    """
    Helper function to create a timeline event with deduplication.
    
    Args:
        visit: Visit instance
        event_type: Event type string
        description: Human-readable description
        actor: User who triggered the event
        source_type: Type of source object (e.g., 'consultation')
        source_id: ID of source object
        metadata: Additional metadata dict
        timestamp: When the event occurred (defaults to now)
    
    Returns:
        TimelineEvent instance or None if duplicate
    """
    if timestamp is None:
        timestamp = timezone.now()
    
    # Generate deduplication key
    source_part = f":{source_id}" if source_id else ""
    deduplication_key = f"{visit.id}:{event_type}{source_part}"
    
    # Check for existing event
    if TimelineEvent.objects.filter(deduplication_key=deduplication_key).exists():
        logger.debug(f"Timeline event already exists: {deduplication_key}")
        return None
    
    try:
        actor_role = getattr(actor, 'role', '') if actor else ''
        
        event = TimelineEvent.objects.create(
            visit=visit,
            event_type=event_type,
            timestamp=timestamp,
            actor=actor,
            actor_role=actor_role,
            description=description,
            source_type=source_type,
            source_id=source_id,
            metadata=metadata or {},
            deduplication_key=deduplication_key
        )
        logger.info(f"Created timeline event: {event_type} for visit {visit.id}")
        return event
    except Exception as e:
        logger.error(f"Error creating timeline event: {e}")
        return None


# Visit signals
@receiver(post_save, sender=Visit)
def log_visit_created(sender, instance, created, **kwargs):
    """Log when a visit is created."""
    if created:
        create_timeline_event(
            visit=instance,
            event_type='VISIT_CREATED',
            description=f"Visit #{instance.id} created for {instance.patient.get_full_name()}",
            actor=getattr(instance, 'created_by', None),
            source_type='visit',
            source_id=instance.id,
            metadata={
                'visit_type': instance.visit_type,
                'payment_type': instance.payment_type,
            }
        )


# Consultation signals
@receiver(post_save, sender=Consultation)
def log_consultation_events(sender, instance, created, **kwargs):
    """Log consultation started/closed events."""
    if created:
        create_timeline_event(
            visit=instance.visit,
            event_type='CONSULTATION_STARTED',
            description=f"Consultation started by {instance.created_by.get_full_name() if instance.created_by else 'System'}",
            actor=instance.created_by,
            source_type='consultation',
            source_id=instance.id,
            metadata={
                'status': instance.status,
            }
        )
    else:
        # Check if status changed to CLOSED
        if hasattr(instance, '_previous_status'):
            if instance._previous_status != 'CLOSED' and instance.status == 'CLOSED':
                create_timeline_event(
                    visit=instance.visit,
                    event_type='CONSULTATION_CLOSED',
                    description=f"Consultation closed by {instance.created_by.get_full_name() if instance.created_by else 'System'}",
                    actor=instance.created_by,
                    source_type='consultation',
                    source_id=instance.id,
                )


@receiver(post_init, sender=Consultation)
def store_previous_consultation_status(sender, instance, **kwargs):
    """Store previous status to detect status changes."""
    # Prevent recursion: if we're already fetching an old instance, skip
    if getattr(_thread_local, 'fetching_consultation_status', False):
        instance._previous_status = None
        return
    
    if instance.pk:
        try:
            # Set flag to prevent recursion
            _thread_local.fetching_consultation_status = True
            # Use only() to fetch only the status field, avoiding full model initialization
            old_instance = Consultation.objects.only('status').get(pk=instance.pk)
            instance._previous_status = old_instance.status
        except Consultation.DoesNotExist:
            instance._previous_status = None
        finally:
            # Always clear the flag
            _thread_local.fetching_consultation_status = False
    else:
        instance._previous_status = None


# Lab Order signals
@receiver(post_save, sender=LabOrder)
def log_lab_ordered(sender, instance, created, **kwargs):
    """Log when a lab order is created."""
    if created:
        tests = ', '.join(instance.tests_requested) if isinstance(instance.tests_requested, list) else str(instance.tests_requested)
        create_timeline_event(
            visit=instance.visit,
            event_type='LAB_ORDERED',
            description=f"Lab order placed: {tests}",
            actor=instance.ordered_by,
            source_type='lab_order',
            source_id=instance.id,
            metadata={
                'tests_requested': instance.tests_requested,
            }
        )


@receiver(post_save, sender=LabResult)
def log_lab_result_posted(sender, instance, created, **kwargs):
    """Log when a lab result is posted."""
    if created:
        lab_order = instance.lab_order
        create_timeline_event(
            visit=lab_order.visit,
            event_type='LAB_RESULT_POSTED',
            description=f"Lab result posted for {lab_order.tests_requested}",
            actor=instance.recorded_by,
            source_type='lab_result',
            source_id=instance.id,
            metadata={
                'abnormal_flag': instance.abnormal_flag,
            }
        )


# Radiology signals
@receiver(post_save, sender=RadiologyRequest)
def log_radiology_ordered(sender, instance, created, **kwargs):
    """Log when a radiology order is created."""
    if created:
        create_timeline_event(
            visit=instance.visit,
            event_type='RADIOLOGY_ORDERED',
            description=f"Radiology study ordered: {instance.study_type}",
            actor=instance.ordered_by,
            source_type='radiology_request',
            source_id=instance.id,
            metadata={
                'study_type': instance.study_type,
            }
        )


@receiver(post_save, sender=RadiologyRequest)
def log_radiology_report_posted(sender, instance, created, **kwargs):
    """Log when a radiology report is posted."""
    if not created and instance.report:
        # Check if report was just added
        if hasattr(instance, '_previous_report') and not instance._previous_report:
            create_timeline_event(
                visit=instance.visit,
                event_type='RADIOLOGY_REPORT_POSTED',
                description=f"Radiology report posted for {instance.study_type}",
                actor=instance.reported_by,
                source_type='radiology_request',
                source_id=instance.id,
                metadata={
                    'study_type': instance.study_type,
                    'report_date': str(instance.report_date) if instance.report_date else None,
                }
            )


@receiver(post_init, sender=RadiologyRequest)
def store_previous_radiology_report(sender, instance, **kwargs):
    """Store previous report to detect when report is added."""
    # Prevent recursion: if we're already fetching an old instance, skip
    if getattr(_thread_local, 'fetching_radiology_report', False):
        instance._previous_report = None
        return
    
    if instance.pk:
        try:
            # Set flag to prevent recursion
            _thread_local.fetching_radiology_report = True
            old_instance = RadiologyRequest.objects.only('report').get(pk=instance.pk)
            instance._previous_report = old_instance.report
        except RadiologyRequest.DoesNotExist:
            instance._previous_report = None
        finally:
            # Always clear the flag
            _thread_local.fetching_radiology_report = False
    else:
        instance._previous_report = None


# Prescription signals
@receiver(post_save, sender=Prescription)
def log_drug_dispensed(sender, instance, created, **kwargs):
    """Log when a drug is dispensed."""
    if not created and instance.dispensed:
        # Check if drug was just dispensed
        if hasattr(instance, '_previous_dispensed') and not instance._previous_dispensed:
            create_timeline_event(
                visit=instance.visit,
                event_type='DRUG_DISPENSED',
                description=f"Drug dispensed: {instance.drug} (Qty: {instance.quantity})",
                actor=instance.dispensed_by,
                source_type='prescription',
                source_id=instance.id,
                metadata={
                    'drug': instance.drug,
                    'quantity': instance.quantity,
                }
            )


@receiver(post_init, sender=Prescription)
def store_previous_dispensed_status(sender, instance, **kwargs):
    """Store previous dispensed status to detect when drug is dispensed."""
    # Prevent recursion: if we're already fetching an old instance, skip
    if getattr(_thread_local, 'fetching_prescription_dispensed', False):
        instance._previous_dispensed = False
        return
    
    if instance.pk:
        try:
            # Set flag to prevent recursion
            _thread_local.fetching_prescription_dispensed = True
            old_instance = Prescription.objects.only('dispensed').get(pk=instance.pk)
            instance._previous_dispensed = old_instance.dispensed
        except Prescription.DoesNotExist:
            instance._previous_dispensed = False
        finally:
            # Always clear the flag
            _thread_local.fetching_prescription_dispensed = False
    else:
        instance._previous_dispensed = False


# Billing signals
@receiver(post_save, sender=BillingLineItem)
def log_payment_confirmed(sender, instance, created, **kwargs):
    """Log when payment is confirmed."""
    if not created and instance.bill_status == 'PAID':
        # Check if status just changed to PAID
        if hasattr(instance, '_previous_bill_status') and instance._previous_bill_status != 'PAID':
            service_name = instance.service_catalog.name if instance.service_catalog else instance.source_service_name
            create_timeline_event(
                visit=instance.visit,
                event_type='PAYMENT_CONFIRMED',
                description=f"Payment confirmed: {service_name} - ₦{instance.amount_paid:,.2f}",
                actor=instance.created_by,
                source_type='billing_line_item',
                source_id=instance.id,
                metadata={
                    'service_name': service_name,
                    'amount': str(instance.amount_paid),
                    'payment_method': instance.payment_method,
                }
            )


@receiver(post_init, sender=BillingLineItem)
def store_previous_bill_status(sender, instance, **kwargs):
    """Store previous bill status to detect when payment is confirmed."""
    # Prevent recursion: if we're already fetching an old instance, skip
    if getattr(_thread_local, 'fetching_billing_status', False):
        instance._previous_bill_status = None
        return
    
    if instance.pk:
        try:
            # Set flag to prevent recursion
            _thread_local.fetching_billing_status = True
            old_instance = BillingLineItem.objects.only('bill_status').get(pk=instance.pk)
            instance._previous_bill_status = old_instance.bill_status
        except BillingLineItem.DoesNotExist:
            instance._previous_bill_status = None
        finally:
            # Always clear the flag
            _thread_local.fetching_billing_status = False
    else:
        instance._previous_bill_status = None


# Service Catalog selection (via BillingLineItem creation)
@receiver(post_save, sender=BillingLineItem)
def log_service_selected(sender, instance, created, **kwargs):
    """Log when a service is selected from catalog."""
    if created:
        service_name = instance.service_catalog.name if instance.service_catalog else instance.source_service_name
        create_timeline_event(
            visit=instance.visit,
            event_type='SERVICE_SELECTED',
            description=f"Service selected: {service_name} - ₦{instance.amount:,.2f}",
            actor=instance.created_by,
            source_type='billing_line_item',
            source_id=instance.id,
            metadata={
                'service_name': service_name,
                'service_code': instance.source_service_code,
                'amount': str(instance.amount),
            }
        )


# Procedure signals
@receiver(post_save, sender=ProcedureTask)
def log_procedure_ordered(sender, instance, created, **kwargs):
    """Log when a procedure is ordered."""
    if created:
        create_timeline_event(
            visit=instance.visit,
            event_type='PROCEDURE_ORDERED',
            description=f"Procedure ordered: {instance.procedure_name}",
            actor=instance.ordered_by,
            source_type='procedure_task',
            source_id=instance.id,
            metadata={
                'procedure_name': instance.procedure_name,
            }
        )


@receiver(post_save, sender=ProcedureTask)
def log_procedure_completed(sender, instance, created, **kwargs):
    """Log when a procedure is completed."""
    if not created and instance.status == ProcedureTask.Status.COMPLETED:
        # Check if status just changed to COMPLETED
        if hasattr(instance, '_previous_status') and instance._previous_status != ProcedureTask.Status.COMPLETED:
            create_timeline_event(
                visit=instance.visit,
                event_type='PROCEDURE_COMPLETED',
                description=f"Procedure completed: {instance.procedure_name}",
                actor=instance.executed_by,
                source_type='procedure_task',
                source_id=instance.id,
                metadata={
                    'procedure_name': instance.procedure_name,
                }
            )


@receiver(post_init, sender=ProcedureTask)
def store_previous_procedure_status(sender, instance, **kwargs):
    """Store previous procedure status to detect when procedure is completed."""
    # Prevent recursion: if we're already fetching an old instance, skip
    if getattr(_thread_local, 'fetching_procedure_status', False):
        instance._previous_status = None
        return
    
    if instance.pk:
        try:
            # Set flag to prevent recursion
            _thread_local.fetching_procedure_status = True
            old_instance = ProcedureTask.objects.only('status').get(pk=instance.pk)
            instance._previous_status = old_instance.status
        except ProcedureTask.DoesNotExist:
            instance._previous_status = None
        finally:
            # Always clear the flag
            _thread_local.fetching_procedure_status = False
    else:
        instance._previous_status = None


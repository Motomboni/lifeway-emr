"""
Revenue Leak Detection Service.

Per EMR Rules:
- Detect leaks idempotently (same leak = same record)
- Exclude emergency overrides
- Do NOT auto-fix leaks
- Leaks must be reviewed and resolved manually
"""
import logging
from typing import Optional, Dict, Any
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from .leak_detection_models import LeakRecord
from .billing_line_item_models import BillingLineItem
from .service_catalog_models import ServiceCatalog

logger = logging.getLogger(__name__)


class LeakDetectionService:
    """
    Service for detecting revenue leaks.
    
    A revenue leak occurs when a clinical action is completed without
    a corresponding paid BillingLineItem.
    """
    
    @staticmethod
    @transaction.atomic
    def detect_lab_result_leak(lab_result_id: int) -> Optional[LeakRecord]:
        """
        Detect revenue leak for LabResult.
        
        Leak condition: LabResult exists but no PAID bill for its ServiceCatalog.
        
        Args:
            lab_result_id: ID of the LabResult to check
        
        Returns:
            LeakRecord if leak detected, None otherwise
        """
        from apps.laboratory.models import LabResult
        
        try:
            lab_result = LabResult.objects.select_related(
                'lab_order',
                'lab_order__visit',
                'lab_order__consultation'
            ).get(pk=lab_result_id)
        except LabResult.DoesNotExist:
            logger.warning(f"LabResult {lab_result_id} not found")
            return None
        
        visit = lab_result.lab_order.visit
        
        # Check if leak already detected (idempotent)
        existing_leak = LeakRecord.objects.filter(
            entity_type='LAB_RESULT',
            entity_id=lab_result_id,
            resolved_at__isnull=True
        ).first()
        
        if existing_leak:
            logger.debug(f"Leak already detected for LabResult {lab_result_id}")
            return existing_leak
        
        # Find ServiceCatalog for this lab order
        # LabOrder should have been created from ServiceCatalog
        # We need to find the BillingLineItem for this visit/service
        service_catalog = None
        estimated_amount = Decimal('0.00')
        
        # Try to find BillingLineItem for this visit
        # Look for LAB workflow type bills
        billing_items = BillingLineItem.objects.filter(
            visit=visit,
            service_catalog__workflow_type='LAB_ORDER',
            service_catalog__department='LAB'
        )
        
        # Check if any are PAID
        paid_bills = billing_items.filter(bill_status='PAID')
        
        if paid_bills.exists():
            # No leak - bill exists and is paid
            logger.debug(f"No leak for LabResult {lab_result_id} - paid bill exists")
            return None
        
        # Check if there's a ServiceCatalog we can use for estimation
        tests_requested = None
        if billing_items.exists():
            service_catalog = billing_items.first().service_catalog
            estimated_amount = service_catalog.amount
        else:
            # Try to find ServiceCatalog by matching test names
            # This is a fallback - ideally ServiceCatalog should be linked
            try:
                tests_requested = lab_result.lab_order.tests_requested
            except AttributeError:
                tests_requested = None
            
            if isinstance(tests_requested, list) and tests_requested:
                # Try to find matching ServiceCatalog
                service_catalog = ServiceCatalog.objects.filter(
                    workflow_type='LAB_ORDER',
                    department='LAB',
                    is_active=True
                ).first()
                
                if service_catalog:
                    estimated_amount = service_catalog.amount
                else:
                    # Default estimate if no ServiceCatalog found
                    estimated_amount = Decimal('5000.00')  # Default lab test price
            else:
                # Default estimate if no tests_requested or not a list
                estimated_amount = Decimal('5000.00')  # Default lab test price
        
        # Create leak record
        leak = LeakRecord.objects.create(
            entity_type='LAB_RESULT',
            entity_id=lab_result_id,
            service_code=service_catalog.service_code if service_catalog else 'UNKNOWN',
            service_name=service_catalog.name if service_catalog else 'Unknown Lab Test',
            estimated_amount=estimated_amount,
            visit=visit,
            detection_context={
                'lab_order_id': lab_result.lab_order.id,
                'tests_requested': tests_requested if tests_requested is not None else [],
                'reason': 'No PAID BillingLineItem found for LabResult'
            }
        )
        
        logger.info(f"Leak detected for LabResult {lab_result_id}: {estimated_amount} NGN")
        return leak
    
    @staticmethod
    @transaction.atomic
    def detect_radiology_report_leak(radiology_request_id: int) -> Optional[LeakRecord]:
        """
        Detect revenue leak for RadiologyReport.
        
        Leak condition: RadiologyRequest has report but no PAID bill.
        
        Args:
            radiology_request_id: ID of the RadiologyRequest to check
        
        Returns:
            LeakRecord if leak detected, None otherwise
        """
        from apps.radiology.models import RadiologyRequest
        
        try:
            radiology_request = RadiologyRequest.objects.select_related(
                'visit',
                'consultation'
            ).get(pk=radiology_request_id)
        except RadiologyRequest.DoesNotExist:
            logger.warning(f"RadiologyRequest {radiology_request_id} not found")
            return None
        
        # Only check if report exists
        if not radiology_request.report:
            logger.debug(f"No report for RadiologyRequest {radiology_request_id}")
            return None
        
        visit = radiology_request.visit
        
        # Check if leak already detected (idempotent)
        existing_leak = LeakRecord.objects.filter(
            entity_type='RADIOLOGY_REPORT',
            entity_id=radiology_request_id,
            resolved_at__isnull=True
        ).first()
        
        if existing_leak:
            logger.debug(f"Leak already detected for RadiologyRequest {radiology_request_id}")
            return existing_leak
        
        # Find ServiceCatalog for this radiology request
        service_catalog = None
        estimated_amount = Decimal('0.00')
        
        # Try to find BillingLineItem for this visit
        billing_items = BillingLineItem.objects.filter(
            visit=visit,
            service_catalog__workflow_type='RADIOLOGY_STUDY',
            service_catalog__department='RADIOLOGY'
        )
        
        # Check if any are PAID
        paid_bills = billing_items.filter(bill_status='PAID')
        
        if paid_bills.exists():
            # No leak - bill exists and is paid
            logger.debug(f"No leak for RadiologyRequest {radiology_request_id} - paid bill exists")
            return None
        
        # Check if there's a ServiceCatalog we can use for estimation
        if billing_items.exists():
            service_catalog = billing_items.first().service_catalog
            estimated_amount = service_catalog.amount
        else:
            # Try to find matching ServiceCatalog
            service_catalog = ServiceCatalog.objects.filter(
                workflow_type='RADIOLOGY_STUDY',
                department='RADIOLOGY',
                is_active=True
            ).first()
            
            if service_catalog:
                estimated_amount = service_catalog.amount
            else:
                # Default estimate
                estimated_amount = Decimal('10000.00')  # Default radiology price
        
        # Create leak record
        leak = LeakRecord.objects.create(
            entity_type='RADIOLOGY_REPORT',
            entity_id=radiology_request_id,
            service_code=service_catalog.service_code if service_catalog else 'UNKNOWN',
            service_name=service_catalog.name if service_catalog else 'Unknown Radiology Study',
            estimated_amount=estimated_amount,
            visit=visit,
            detection_context={
                'study_type': radiology_request.study_type,
                'reason': 'No PAID BillingLineItem found for RadiologyRequest with report'
            }
        )
        
        logger.info(f"Leak detected for RadiologyRequest {radiology_request_id}: {estimated_amount} NGN")
        return leak
    
    @staticmethod
    @transaction.atomic
    def detect_drug_dispense_leak(prescription_id: int) -> Optional[LeakRecord]:
        """
        Detect revenue leak for DrugDispense.
        
        Leak condition: Prescription is dispensed but no PAID bill.
        Excludes emergency overrides.
        
        Args:
            prescription_id: ID of the Prescription to check
        
        Returns:
            LeakRecord if leak detected, None otherwise
        """
        from apps.pharmacy.models import Prescription
        
        try:
            prescription = Prescription.objects.select_related(
                'visit',
                'consultation'
            ).get(pk=prescription_id)
        except Prescription.DoesNotExist:
            logger.warning(f"Prescription {prescription_id} not found")
            return None
        
        # Only check if dispensed
        if not prescription.dispensed:
            logger.debug(f"Prescription {prescription_id} not dispensed")
            return None
        
        # Exclude emergency overrides
        if prescription.is_emergency:
            logger.debug(f"Prescription {prescription_id} is emergency - excluded from leak detection")
            return None
        
        visit = prescription.visit
        
        # Check if leak already detected (idempotent)
        existing_leak = LeakRecord.objects.filter(
            entity_type='DRUG_DISPENSE',
            entity_id=prescription_id,
            resolved_at__isnull=True
        ).first()
        
        if existing_leak:
            logger.debug(f"Leak already detected for Prescription {prescription_id}")
            return existing_leak
        
        # Find ServiceCatalog for this prescription
        service_catalog = None
        estimated_amount = Decimal('0.00')
        
        # Try to find BillingLineItem for this visit
        billing_items = BillingLineItem.objects.filter(
            visit=visit,
            service_catalog__workflow_type='DRUG_DISPENSE',
            service_catalog__department='PHARMACY'
        )
        
        # Check if any are PAID
        paid_bills = billing_items.filter(bill_status='PAID')
        
        if paid_bills.exists():
            # No leak - bill exists and is paid
            logger.debug(f"No leak for Prescription {prescription_id} - paid bill exists")
            return None
        
        # Check if there's a ServiceCatalog we can use for estimation
        if billing_items.exists():
            service_catalog = billing_items.first().service_catalog
            estimated_amount = service_catalog.amount
        else:
            # Try to find matching ServiceCatalog
            service_catalog = ServiceCatalog.objects.filter(
                workflow_type='DRUG_DISPENSE',
                department='PHARMACY',
                is_active=True
            ).first()
            
            if service_catalog:
                estimated_amount = service_catalog.amount
            else:
                # Default estimate
                estimated_amount = Decimal('3000.00')  # Default drug price
        
        # Create leak record
        leak = LeakRecord.objects.create(
            entity_type='DRUG_DISPENSE',
            entity_id=prescription_id,
            service_code=service_catalog.service_code if service_catalog else 'UNKNOWN',
            service_name=service_catalog.name if service_catalog else prescription.drug,
            estimated_amount=estimated_amount,
            visit=visit,
            detection_context={
                'drug': prescription.drug,
                'quantity': prescription.quantity,
                'reason': 'No PAID BillingLineItem found for dispensed Prescription'
            }
        )
        
        logger.info(f"Leak detected for Prescription {prescription_id}: {estimated_amount} NGN")
        return leak
    
    @staticmethod
    @transaction.atomic
    def detect_procedure_leak(procedure_task_id: int) -> Optional[LeakRecord]:
        """
        Detect revenue leak for Procedure.
        
        Leak condition: ProcedureTask is COMPLETED but no PAID bill.
        
        Args:
            procedure_task_id: ID of the ProcedureTask to check
        
        Returns:
            LeakRecord if leak detected, None otherwise
        """
        from apps.clinical.procedure_models import ProcedureTask
        
        try:
            procedure_task = ProcedureTask.objects.select_related(
                'visit',
                'consultation',
                'service_catalog'
            ).get(pk=procedure_task_id)
        except ProcedureTask.DoesNotExist:
            logger.warning(f"ProcedureTask {procedure_task_id} not found")
            return None
        
        # Only check if completed
        if procedure_task.status != 'COMPLETED':
            logger.debug(f"ProcedureTask {procedure_task_id} not completed")
            return None
        
        visit = procedure_task.visit
        
        # Check if leak already detected (idempotent)
        existing_leak = LeakRecord.objects.filter(
            entity_type='PROCEDURE',
            entity_id=procedure_task_id,
            resolved_at__isnull=True
        ).first()
        
        if existing_leak:
            logger.debug(f"Leak already detected for ProcedureTask {procedure_task_id}")
            return existing_leak
        
        # Use ServiceCatalog from procedure_task
        service_catalog = procedure_task.service_catalog
        estimated_amount = service_catalog.amount if service_catalog else Decimal('5000.00')
        
        # Check if there's a PAID BillingLineItem
        billing_items = BillingLineItem.objects.filter(
            visit=visit,
            service_catalog=service_catalog,
            bill_status='PAID'
        )
        
        if billing_items.exists():
            # No leak - bill exists and is paid
            logger.debug(f"No leak for ProcedureTask {procedure_task_id} - paid bill exists")
            return None
        
        # Create leak record
        leak = LeakRecord.objects.create(
            entity_type='PROCEDURE',
            entity_id=procedure_task_id,
            service_code=service_catalog.service_code if service_catalog else 'UNKNOWN',
            service_name=service_catalog.name if service_catalog else procedure_task.procedure_name,
            estimated_amount=estimated_amount,
            visit=visit,
            detection_context={
                'procedure_name': procedure_task.procedure_name,
                'reason': 'No PAID BillingLineItem found for completed ProcedureTask'
            }
        )
        
        logger.info(f"Leak detected for ProcedureTask {procedure_task_id}: {estimated_amount} NGN")
        return leak
    
    @staticmethod
    def detect_all_leaks():
        """
        Detect all leaks in the system.
        
        This method scans all entities and detects leaks.
        Should be run periodically (e.g., daily).
        
        Returns:
            Dict with detection results
        """
        results = {
            'lab_results': 0,
            'radiology_reports': 0,
            'drug_dispenses': 0,
            'procedures': 0,
            'total_leaks': 0,
            'total_estimated_loss': Decimal('0.00')
        }
        
        # Detect LabResult leaks - use select_related for optimization
        from apps.laboratory.models import LabResult
        lab_results = LabResult.objects.select_related('lab_order', 'lab_order__visit').all()
        for lab_result in lab_results:
            try:
                leak = LeakDetectionService.detect_lab_result_leak(lab_result.id)
                if leak:
                    results['lab_results'] += 1
                    results['total_leaks'] += 1
                    results['total_estimated_loss'] += leak.estimated_amount
            except Exception as e:
                logger.warning(f"Error detecting leak for LabResult {lab_result.id}: {e}")
                continue
        
        # Detect RadiologyReport leaks - use select_related for optimization
        from apps.radiology.models import RadiologyRequest
        radiology_requests = RadiologyRequest.objects.select_related('visit', 'consultation').exclude(
            report__isnull=True
        ).exclude(report='')
        for radiology_request in radiology_requests:
            try:
                leak = LeakDetectionService.detect_radiology_report_leak(radiology_request.id)
                if leak:
                    results['radiology_reports'] += 1
                    results['total_leaks'] += 1
                    results['total_estimated_loss'] += leak.estimated_amount
            except Exception as e:
                logger.warning(f"Error detecting leak for RadiologyRequest {radiology_request.id}: {e}")
                continue
        
        # Detect DrugDispense leaks - use select_related for optimization
        from apps.pharmacy.models import Prescription
        prescriptions = Prescription.objects.select_related('visit', 'consultation').filter(
            dispensed=True, is_emergency=False
        )
        for prescription in prescriptions:
            try:
                leak = LeakDetectionService.detect_drug_dispense_leak(prescription.id)
                if leak:
                    results['drug_dispenses'] += 1
                    results['total_leaks'] += 1
                    results['total_estimated_loss'] += leak.estimated_amount
            except Exception as e:
                logger.warning(f"Error detecting leak for Prescription {prescription.id}: {e}")
                continue
        
        # Detect Procedure leaks - use select_related for optimization
        from apps.clinical.procedure_models import ProcedureTask
        procedure_tasks = ProcedureTask.objects.select_related(
            'visit', 'consultation', 'service_catalog'
        ).filter(status='COMPLETED')
        for procedure_task in procedure_tasks:
            try:
                leak = LeakDetectionService.detect_procedure_leak(procedure_task.id)
                if leak:
                    results['procedures'] += 1
                    results['total_leaks'] += 1
                    results['total_estimated_loss'] += leak.estimated_amount
            except Exception as e:
                logger.warning(f"Error detecting leak for ProcedureTask {procedure_task.id}: {e}")
                continue
        
        return results
    
    @staticmethod
    def get_daily_aggregation(date=None):
        """
        Get daily aggregation of leaks.
        
        Args:
            date: Date to aggregate (defaults to today)
        
        Returns:
            Dict with daily aggregation data
        """
        from django.db.models import Sum, Count, Q
        from datetime import date as date_type
        
        if date is None:
            date = timezone.now().date()
        
        from datetime import datetime, time as time_type
        
        if isinstance(date, date_type):
            date_start = timezone.make_aware(datetime.combine(date, time_type.min))
            date_end = timezone.make_aware(datetime.combine(date, time_type.max))
        else:
            date_start = date
            date_end = date
        
        # Get leaks detected on this date
        leaks = LeakRecord.objects.filter(
            detected_at__date=date if isinstance(date, date_type) else date_start.date()
        )
        
        # Aggregate by entity type
        aggregation = leaks.values('entity_type').annotate(
            count=Count('id'),
            total_amount=Sum('estimated_amount')
        )
        
        # Get resolved vs unresolved
        unresolved = leaks.filter(resolved_at__isnull=True).aggregate(
            count=Count('id'),
            total_amount=Sum('estimated_amount')
        )
        
        resolved = leaks.filter(resolved_at__isnull=False).aggregate(
            count=Count('id'),
            total_amount=Sum('estimated_amount')
        )
        
        return {
            'date': date if isinstance(date, date_type) else date_start.date(),
            'total_leaks': leaks.count(),
            'total_estimated_loss': leaks.aggregate(Sum('estimated_amount'))['estimated_amount__sum'] or Decimal('0.00'),
            'unresolved': {
                'count': unresolved['count'] or 0,
                'total_amount': unresolved['total_amount'] or Decimal('0.00')
            },
            'resolved': {
                'count': resolved['count'] or 0,
                'total_amount': resolved['total_amount'] or Decimal('0.00')
            },
            'by_entity_type': list(aggregation)
        }


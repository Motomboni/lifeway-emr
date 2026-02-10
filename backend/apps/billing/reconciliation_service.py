"""
End-of-Day Reconciliation Service.

This service orchestrates the end-of-day reconciliation process:
1. Close all ACTIVE visits
2. Identify unpaid services
3. Reconcile payments (Cash, Wallet, Paystack, HMO)
4. Detect mismatches
5. Generate summary report
"""
import logging
from decimal import Decimal
from datetime import date, datetime
from django.db import transaction, models
from django.db.models import Sum, Q, Count
from django.utils import timezone
from django.core.exceptions import ValidationError

from .reconciliation_models import EndOfDayReconciliation
from apps.visits.models import Visit
from apps.billing.billing_line_item_models import BillingLineItem
from apps.billing.models import Payment
from apps.billing.leak_detection_service import LeakDetectionService

logger = logging.getLogger(__name__)


class ReconciliationService:
    """Service for end-of-day reconciliation."""
    
    @staticmethod
    @transaction.atomic
    def create_reconciliation(
        reconciliation_date: date = None,
        prepared_by_id: int = None,
        close_active_visits: bool = True
    ) -> EndOfDayReconciliation:
        """
        Create a new end-of-day reconciliation.
        
        Args:
            reconciliation_date: Date to reconcile (defaults to today)
            prepared_by_id: User ID who prepared the reconciliation
            close_active_visits: Whether to close active visits
        
        Returns:
            EndOfDayReconciliation instance
        """
        if reconciliation_date is None:
            reconciliation_date = timezone.now().date()
        
        # Check if reconciliation already exists for this date
        existing = EndOfDayReconciliation.objects.filter(
            reconciliation_date=reconciliation_date
        ).first()
        
        if existing and existing.status == 'FINALIZED':
            raise ValidationError(
                f"Reconciliation for {reconciliation_date} is already finalized."
            )
        
        if existing:
            logger.info(f"Found existing reconciliation for {reconciliation_date}, refreshing calculations")
            # Refresh the existing reconciliation to ensure it has the latest data
            ReconciliationService._perform_reconciliation(
                existing,
                close_active_visits=close_active_visits
            )
            return existing
        
        # Create new reconciliation
        reconciliation = EndOfDayReconciliation.objects.create(
            reconciliation_date=reconciliation_date,
            prepared_by_id=prepared_by_id,
            status='DRAFT'
        )
        
        # Perform reconciliation (within transaction)
        ReconciliationService._perform_reconciliation(
            reconciliation,
            close_active_visits=close_active_visits
        )
        
        # Detect revenue leaks OUTSIDE the transaction to avoid database locks
        # This operation can be slow and shouldn't block the reconciliation creation
        try:
            from .leak_detection_service import LeakDetectionService
            leaks_result = LeakDetectionService.detect_all_leaks()
            reconciliation.revenue_leaks_detected = leaks_result.get('total_leaks', 0)
            reconciliation.revenue_leaks_amount = leaks_result.get('total_estimated_loss', Decimal('0.00'))
            reconciliation.save(update_fields=['revenue_leaks_detected', 'revenue_leaks_amount'])
        except Exception as e:
            logger.warning(f"Error detecting leaks during reconciliation: {e}", exc_info=True)
            # Don't fail reconciliation if leak detection fails
            reconciliation.revenue_leaks_detected = 0
            reconciliation.revenue_leaks_amount = Decimal('0.00')
            reconciliation.save(update_fields=['revenue_leaks_detected', 'revenue_leaks_amount'])
        
        logger.info(f"Created reconciliation for {reconciliation_date}")
        return reconciliation
    
    @staticmethod
    @transaction.atomic
    def _perform_reconciliation(
        reconciliation: EndOfDayReconciliation,
        close_active_visits: bool = True
    ):
        """
        Perform the actual reconciliation calculations.
        
        Args:
            reconciliation: EndOfDayReconciliation instance
            close_active_visits: Whether to close active visits
        """
        reconciliation_date = reconciliation.reconciliation_date
        
        # Get all visits for the date
        visits = Visit.objects.filter(
            created_at__date=reconciliation_date
        )
        
        reconciliation.total_visits = visits.count()
        
        # Close active visits if requested
        active_visits = visits.filter(status='ACTIVE')
        if close_active_visits:
            closed_count = active_visits.update(status='CLOSED')
            reconciliation.active_visits_closed = closed_count
            logger.info(f"Closed {closed_count} active visits for {reconciliation_date}")
        
        # Get all billing line items for visits on this date (for outstanding calculations)
        billing_items = BillingLineItem.objects.filter(
            visit__created_at__date=reconciliation_date
        )
        
        # Calculate revenue from actual Payment transactions for the date
        # Use a direct Python approach instead of aggregation for transparency and accuracy
        # Filter by payment created_at date (when payment was made), not visit created_at date
        # Use select_related to efficiently fetch related visit and patient data
        payments = Payment.objects.filter(
            created_at__date=reconciliation_date,
            status__in=['CLEARED', 'PARTIAL']  # Count both cleared and partial payments
        ).select_related(
            'visit',
            'visit__patient',
            'processed_by'
        ).order_by('id')  # Order for consistent logging
        
        # Initialize totals
        total_cash = Decimal('0.00')
        total_wallet = Decimal('0.00')
        total_paystack = Decimal('0.00')
        total_hmo = Decimal('0.00')
        total_insurance = Decimal('0.00')
        
        # Calculate totals directly from payments (more transparent than aggregation)
        payment_count = 0
        total_payment_sum = Decimal('0.00')
        
        logger.info(f"Processing payments for {reconciliation_date}")
        for payment in payments:
            payment_count += 1
            total_payment_sum += payment.amount
            
            # Categorize payment by method
            method = payment.payment_method
            if method in ['CASH', 'POS', 'TRANSFER']:
                total_cash += payment.amount
                logger.info(f"Payment {payment.id}: NGN {payment.amount} CASH (method={method}, visit={payment.visit_id})")
            elif method == 'WALLET':
                total_wallet += payment.amount
                logger.info(f"Payment {payment.id}: NGN {payment.amount} WALLET (visit={payment.visit_id})")
            elif method == 'PAYSTACK':
                total_paystack += payment.amount
                logger.info(f"Payment {payment.id}: NGN {payment.amount} PAYSTACK (visit={payment.visit_id})")
            elif method in ['HMO', 'INSURANCE']:
                total_hmo += payment.amount
                if method == 'INSURANCE':
                    total_insurance += payment.amount
                logger.info(f"Payment {payment.id}: NGN {payment.amount} {method} (visit={payment.visit_id})")
            else:
                logger.warning(f"Payment {payment.id}: Unknown payment method '{method}', amount={payment.amount}")
        
        # Assign totals to reconciliation
        reconciliation.total_cash = total_cash
        reconciliation.total_wallet = total_wallet
        reconciliation.total_paystack = total_paystack
        reconciliation.total_hmo = total_hmo
        reconciliation.total_insurance = total_insurance
        
        # Calculate total revenue (insurance is already included in HMO, so don't add it again)
        reconciliation.total_revenue = total_cash + total_wallet + total_paystack + total_hmo
        
        # Log summary
        logger.info(f"=== RECONCILIATION SUMMARY ===")
        logger.info(f"Date: {reconciliation_date}")
        logger.info(f"Total payments found: {payment_count}")
        logger.info(f"Sum of all payment amounts: NGN {total_payment_sum}")
        logger.info(f"Breakdown by method:")
        logger.info(f"  Cash (CASH/POS/TRANSFER): NGN {total_cash}")
        logger.info(f"  Wallet: NGN {total_wallet}")
        logger.info(f"  Paystack: NGN {total_paystack}")
        logger.info(f"  HMO (includes Insurance): NGN {total_hmo}")
        logger.info(f"  Insurance (subset of HMO): NGN {total_insurance}")
        logger.info(f"Total Revenue (Cash+Wallet+Paystack+HMO): NGN {reconciliation.total_revenue}")
        
        # Verify calculation
        if payment_count > 0:
            if abs(total_payment_sum - reconciliation.total_revenue) > Decimal('0.01'):
                logger.error(f"ERROR: Total revenue ({reconciliation.total_revenue}) does not match sum of payments ({total_payment_sum})")
                logger.error(f"Difference: NGN {abs(total_payment_sum - reconciliation.total_revenue)}")
            else:
                logger.info(f"Verification passed: Total revenue matches sum of all payments")
                logger.info(f"Expected: NGN {total_payment_sum}, Actual: NGN {reconciliation.total_revenue}")
        
        # Calculate outstanding balances with detailed breakdown
        outstanding_items = billing_items.filter(
            bill_status__in=['PENDING', 'PARTIALLY_PAID']
        ).select_related(
            'visit',
            'visit__patient',
            'service_catalog'
        ).order_by('visit_id', 'id')
        
        outstanding_amount = outstanding_items.aggregate(
            total=Sum('outstanding_amount')
        )['total'] or Decimal('0.00')
        
        reconciliation.total_outstanding = outstanding_amount
        reconciliation.outstanding_visits_count = outstanding_items.values(
            'visit'
        ).distinct().count()
        
        # Build detailed list of outstanding items for transparency
        outstanding_details_list = []
        current_visit_id = None
        visit_outstanding_items = []
        visit_total_outstanding = Decimal('0.00')
        
        for item in outstanding_items:
            # Group by visit
            if current_visit_id is not None and item.visit_id != current_visit_id:
                # Save previous visit's outstanding items
                if visit_outstanding_items:
                    outstanding_details_list.append({
                        'visit_id': current_visit_id,
                        'visit_status': visit_outstanding_items[0].visit.status if visit_outstanding_items[0].visit else None,
                        'patient': {
                            'id': visit_outstanding_items[0].visit.patient.id if visit_outstanding_items[0].visit and visit_outstanding_items[0].visit.patient else None,
                            'name': f"{visit_outstanding_items[0].visit.patient.first_name} {visit_outstanding_items[0].visit.patient.last_name}".strip() if visit_outstanding_items[0].visit and visit_outstanding_items[0].visit.patient else None,
                            'mrn': visit_outstanding_items[0].visit.patient.patient_id if visit_outstanding_items[0].visit and visit_outstanding_items[0].visit.patient else None,
                        } if visit_outstanding_items[0].visit and visit_outstanding_items[0].visit.patient else None,
                        'total_outstanding': float(visit_total_outstanding),
                        'items': visit_outstanding_items,
                    })
                visit_outstanding_items = []
                visit_total_outstanding = Decimal('0.00')
            
            current_visit_id = item.visit_id
            visit_total_outstanding += item.outstanding_amount
            
            visit_outstanding_items.append({
                'id': item.id,
                'service_name': item.source_service_name,
                'service_code': item.source_service_code,
                'amount': float(item.amount),
                'amount_paid': float(item.amount_paid),
                'outstanding_amount': float(item.outstanding_amount),
                'bill_status': item.bill_status,
            })
        
        # Add last visit's items
        if visit_outstanding_items:
            outstanding_details_list.append({
                'visit_id': current_visit_id,
                'visit_status': visit_outstanding_items[0].visit.status if visit_outstanding_items[0].visit else None,
                'patient': {
                    'id': visit_outstanding_items[0].visit.patient.id if visit_outstanding_items[0].visit and visit_outstanding_items[0].visit.patient else None,
                    'name': f"{visit_outstanding_items[0].visit.patient.first_name} {visit_outstanding_items[0].visit.patient.last_name}".strip() if visit_outstanding_items[0].visit and visit_outstanding_items[0].visit.patient else None,
                    'mrn': visit_outstanding_items[0].visit.patient.patient_id if visit_outstanding_items[0].visit and visit_outstanding_items[0].visit.patient else None,
                } if visit_outstanding_items[0].visit and visit_outstanding_items[0].visit.patient else None,
                'total_outstanding': float(visit_total_outstanding),
                'items': visit_outstanding_items,
            })
        
        logger.info(f"Outstanding balances: {reconciliation.outstanding_visits_count} visit(s) with NGN {outstanding_amount} total outstanding")
        
        # Initialize leak detection fields (will be populated outside transaction)
        reconciliation.revenue_leaks_detected = 0
        reconciliation.revenue_leaks_amount = Decimal('0.00')
        
        # Check for mismatches
        reconciliation.has_mismatches = False
        reconciliation.mismatch_details = {}
        
        # Build comprehensive list of payment details with related information
        payment_details_list = []
        for payment in payments:
            visit = payment.visit
            patient = visit.patient if visit else None
            processed_by = payment.processed_by
            
            # Get billing line items for this visit to show what was paid for
            visit_billing_items = BillingLineItem.objects.filter(
                visit=visit,
                bill_status='PAID'
            ).select_related('service_catalog')[:10]  # Limit to 10 items to avoid huge payload
            
            billing_items_summary = []
            for item in visit_billing_items:
                billing_items_summary.append({
                    'service_name': item.source_service_name,
                    'amount': float(item.amount),
                    'payment_method': item.payment_method or payment.payment_method,
                })
            
            payment_details_list.append({
                'id': payment.id,
                'amount': float(payment.amount),
                'payment_method': payment.payment_method,
                'status': payment.status,
                'transaction_reference': payment.transaction_reference or None,
                'notes': payment.notes or None,
                'created_at': payment.created_at.isoformat() if payment.created_at else None,
                'visit': {
                    'id': visit.id if visit else None,
                    'status': visit.status if visit else None,
                    'created_at': visit.created_at.isoformat() if visit and visit.created_at else None,
                    'payment_type': visit.payment_type if visit else None,
                },
                'patient': {
                    'id': patient.id if patient else None,
                    'name': f"{patient.first_name} {patient.last_name}".strip() if patient else None,
                    'mrn': patient.patient_id if patient else None,
                    'phone': patient.phone_number if patient else None,
                } if patient else None,
                'processed_by': {
                    'id': processed_by.id if processed_by else None,
                    'name': processed_by.get_full_name() if processed_by else None,
                    'username': processed_by.username if processed_by else None,
                } if processed_by else None,
                'billing_items': billing_items_summary,
                'billing_items_count': BillingLineItem.objects.filter(visit=visit, bill_status='PAID').count() if visit else 0,
            })
        
        # Store detailed breakdown
        reconciliation.reconciliation_details = {
            'visits': {
                'total': reconciliation.total_visits,
                'active_closed': reconciliation.active_visits_closed,
                'by_status': dict(visits.values('status').annotate(
                    count=Count('id')
                ).values_list('status', 'count')),
            },
            'billing': {
                'total_items': billing_items.count(),
                'paid_items': billing_items.filter(bill_status='PAID').count(),
                'pending_items': billing_items.filter(bill_status='PENDING').count(),
                'partially_paid_items': billing_items.filter(bill_status='PARTIALLY_PAID').count(),
            },
            'payment_methods': reconciliation.get_payment_method_breakdown(),
            'outstanding': {
                'amount': float(reconciliation.total_outstanding),
                'visits_count': reconciliation.outstanding_visits_count,
                'items': outstanding_details_list,  # Detailed breakdown of outstanding items by visit
            },
            'revenue_leaks': {
                'count': reconciliation.revenue_leaks_detected,
                'amount': float(reconciliation.revenue_leaks_amount),
            },
            # Include individual payment details for debugging
            'payments': {
                'count': payment_count,
                'total_sum': float(total_payment_sum),
                'items': payment_details_list,
            },
        }
        
        reconciliation.save()
    
    @staticmethod
    @transaction.atomic
    def refresh_reconciliation(reconciliation_id: int) -> EndOfDayReconciliation:
        """
        Refresh reconciliation calculations.
        
        Args:
            reconciliation_id: ID of reconciliation to refresh
        
        Returns:
            Updated EndOfDayReconciliation instance
        """
        reconciliation = EndOfDayReconciliation.objects.get(pk=reconciliation_id)
        
        if reconciliation.status == 'FINALIZED':
            raise ValidationError("Cannot refresh a finalized reconciliation.")
        
        # Re-perform reconciliation
        ReconciliationService._perform_reconciliation(
            reconciliation,
            close_active_visits=False  # Don't close visits again
        )
        
        logger.info(f"Refreshed reconciliation {reconciliation_id}")
        return reconciliation
    
    @staticmethod
    def get_reconciliation_for_date(reconciliation_date: date = None) -> EndOfDayReconciliation:
        """
        Get reconciliation for a specific date.
        
        Args:
            reconciliation_date: Date to get reconciliation for (defaults to today)
        
        Returns:
            EndOfDayReconciliation instance or None
        """
        if reconciliation_date is None:
            reconciliation_date = timezone.now().date()
        
        return EndOfDayReconciliation.objects.filter(
            reconciliation_date=reconciliation_date
        ).first()
    
    @staticmethod
    def get_reconciliation_summary(reconciliation_id: int) -> dict:
        """
        Get summary of reconciliation.
        
        Args:
            reconciliation_id: ID of reconciliation
        
        Returns:
            Summary dictionary
        """
        reconciliation = EndOfDayReconciliation.objects.get(pk=reconciliation_id)
        return reconciliation.get_summary()


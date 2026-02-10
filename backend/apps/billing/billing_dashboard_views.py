"""
Receptionist Billing Dashboard API.

Per EMR Rules:
- Real-time accurate totals
- Support partial payments
- Support insurance view mode
- Group bill items by department
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, ValidationError as DRFValidationError
from django.db.models import Sum, Q
from decimal import Decimal
from collections import defaultdict

from apps.visits.models import Visit
from apps.billing.bill_models import Bill, BillItem, BillPayment, InsurancePolicy
from apps.billing.price_lists import ServicePriceListManager
from .permissions import CanProcessPayment
from core.audit import AuditLog


class VisitBillingSummaryView(APIView):
    """
    GET /api/billing/visit/{visit_id}/summary/
    
    Get comprehensive billing summary for a visit.
    
    Query Parameters:
    - insurance_view: true/false (default: false) - Show insurance-specific view
    
    Response includes:
    - Patient details
    - Visit status
    - Bill items grouped by department
    - Total bill
    - Amount paid
    - Outstanding balance
    - Payment history
    - Insurance information (if applicable)
    """
    permission_classes = [IsAuthenticated, CanProcessPayment]
    
    def get_visit(self, visit_id):
        """Get visit and verify access."""
        try:
            visit = Visit.objects.get(id=visit_id)
        except Visit.DoesNotExist:
            raise NotFound(f"Visit with id {visit_id} not found.")
        
        return visit
    
    def get(self, request, visit_id):
        """
        Get billing summary for a visit.
        
        Returns real-time accurate totals and comprehensive billing information.
        """
        visit = self.get_visit(visit_id)
        
        # Check if insurance view mode is requested
        insurance_view = request.query_params.get('insurance_view', 'false').lower() == 'true'
        
        # Get or create bill for visit
        try:
            bill = Bill.objects.get(visit=visit)
        except Bill.DoesNotExist:
            # Create empty bill if it doesn't exist
            bill = Bill.objects.create(visit=visit)
        
        # Recalculate totals to ensure accuracy (real-time)
        bill.recalculate_totals()
        bill.save(update_fields=['total_amount', 'amount_paid', 'outstanding_balance', 'status'])
        
        # Get patient details
        patient = visit.patient
        patient_details = {
            'id': patient.id,
            'patient_id': patient.patient_id,
            'full_name': patient.get_full_name() or f"{patient.first_name} {patient.last_name}".strip(),
            'first_name': patient.first_name,
            'last_name': patient.last_name,
            'email': patient.email or '',
            'phone': patient.phone or '',
            'date_of_birth': patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            'gender': patient.gender or '',
        }
        
        # Get bill items grouped by department
        bill_items = BillItem.objects.filter(bill=bill).order_by('department', 'created_at')
        
        items_by_department = defaultdict(list)
        for item in bill_items:
            items_by_department[item.department].append({
                'id': item.id,
                'service_name': item.service_name,
                'amount': str(item.amount),
                'status': item.status,
                'created_at': item.created_at.isoformat(),
            })
        
        # Convert to list format with department totals
        department_summary = []
        for department, items in items_by_department.items():
            department_total = sum(Decimal(item['amount']) for item in items)
            department_summary.append({
                'department': department,
                'items': items,
                'item_count': len(items),
                'total_amount': str(department_total),
            })
        
        # Sort by department name
        department_summary.sort(key=lambda x: x['department'])
        
        # Get payment history
        payments = BillPayment.objects.filter(bill=bill).order_by('-created_at')
        payment_history = [
            {
                'id': payment.id,
                'amount': str(payment.amount),
                'payment_method': payment.payment_method,
                'transaction_reference': payment.transaction_reference or '',
                'notes': payment.notes or '',
                'processed_by': payment.processed_by.get_full_name() or str(payment.processed_by),
                'created_at': payment.created_at.isoformat(),
            }
            for payment in payments
        ]
        
        # Get insurance information (if applicable)
        insurance_info = None
        if bill.is_insurance_backed and bill.insurance_policy:
            policy = bill.insurance_policy
            insurance_info = {
                'provider_name': policy.provider.name,
                'provider_code': policy.provider.code or '',
                'policy_number': policy.policy_number,
                'coverage_type': policy.coverage_type,
                'coverage_percentage': str(policy.coverage_percentage),
                'is_valid': policy.is_valid(),
                'valid_from': policy.valid_from.isoformat(),
                'valid_to': policy.valid_to.isoformat() if policy.valid_to else None,
            }
        
        # Calculate insurance coverage (if insurance-backed)
        insurance_coverage = None
        if bill.is_insurance_backed and bill.insurance_policy:
            policy = bill.insurance_policy
            if policy.is_valid():
                # Calculate insurance amount based on coverage
                if policy.coverage_type == 'FULL':
                    insurance_coverage = bill.total_amount
                else:
                    # Partial coverage
                    coverage_percentage = policy.coverage_percentage / Decimal('100.00')
                    insurance_coverage = bill.total_amount * coverage_percentage
                
                # Patient payable after insurance
                patient_payable_after_insurance = bill.total_amount - insurance_coverage
            else:
                # Policy not valid - patient pays full amount
                insurance_coverage = Decimal('0.00')
                patient_payable_after_insurance = bill.total_amount
        else:
            patient_payable_after_insurance = bill.total_amount
        
        # Build response
        response_data = {
            'visit_id': visit.id,
            'visit_status': visit.status,
            'visit_type': visit.visit_type or '',
            'chief_complaint': visit.chief_complaint or '',
            'created_at': visit.created_at.isoformat(),
            
            'patient': patient_details,
            
            'bill': {
                'id': bill.id,
                'is_insurance_backed': bill.is_insurance_backed,
                'total_amount': str(bill.total_amount),
                'amount_paid': str(bill.amount_paid),
                'outstanding_balance': str(bill.outstanding_balance),
                'status': bill.status,
            },
            
            'items_by_department': department_summary,
            'total_items': len(bill_items),
            
            'payment_history': payment_history,
            'payment_count': len(payments),
            
            'insurance': insurance_info,
            'insurance_coverage': str(insurance_coverage) if insurance_coverage is not None else None,
            'patient_payable_after_insurance': str(patient_payable_after_insurance) if insurance_coverage is not None else None,
            
            'summary': {
                'total_bill': str(bill.total_amount),
                'total_paid': str(bill.amount_paid),
                'outstanding_balance': str(bill.outstanding_balance),
                'payment_status': bill.status,
                'can_accept_payment': bill.outstanding_balance > 0 and visit.status == 'OPEN',
                'is_fully_paid': bill.outstanding_balance <= 0,
                'is_partially_paid': bill.amount_paid > 0 and bill.outstanding_balance > 0,
            },
        }
        
        # Add insurance-specific view if requested
        if insurance_view and bill.is_insurance_backed:
            response_data['insurance_view'] = {
                'insurance_amount': str(insurance_coverage) if insurance_coverage else '0.00',
                'patient_payable': str(patient_payable_after_insurance) if patient_payable_after_insurance else str(bill.total_amount),
                'patient_paid': str(bill.amount_paid),
                'patient_outstanding': str(max(Decimal('0.00'), patient_payable_after_insurance - bill.amount_paid)),
                'insurance_status': 'COVERED' if insurance_coverage and insurance_coverage >= bill.total_amount else 'PARTIAL' if insurance_coverage else 'PENDING',
            }
        
        # Audit log
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        AuditLog.log(
            user=request.user,
            role=user_role,
            action="BILLING_SUMMARY_VIEWED",
            visit_id=visit.id,
            resource_type="bill",
            resource_id=bill.id,
            request=request
        )
        
        return Response(response_data, status=status.HTTP_200_OK)


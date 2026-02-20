"""
Centralized Billing Service - Deterministic and Auditable.

Per EMR Rules:
- Billing logic MUST NOT live in views
- Billing computation must be deterministic and auditable
- All billing calculations centralized in this service

Inputs:
- VisitCharges
- Payments
- Wallet debits
- Insurance coverage

Outputs:
- Total charges
- Insurance-covered amount
- Patient payable amount
- Outstanding balance
- payment_status
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Dict, Any  # noqa: F401 - Optional used in dataclass
from django.db.models import Sum, Q
from django.core.exceptions import ValidationError

from .models import VisitCharge, Payment
from .insurance_models import VisitInsurance
from apps.wallet.models import WalletTransaction


@dataclass
class BillingSummary:
    """
    Structured billing summary for a Visit.
    
    All amounts are Decimal for precision.
    """
    # Input totals
    total_charges: Decimal
    total_payments: Decimal
    total_wallet_debits: Decimal
    
    # Retainership
    has_retainership: bool
    retainership_discount: Decimal
    retainership_discount_percentage: Decimal
    charges_after_retainership: Decimal  # Total charges after retainership discount
    
    # Insurance
    has_insurance: bool
    insurance_status: Optional[str]  # PENDING, APPROVED, REJECTED
    insurance_amount: Decimal
    insurance_coverage_type: Optional[str]  # FULL, PARTIAL
    
    # Computed amounts
    patient_payable: Decimal
    outstanding_balance: Decimal
    
    # Status
    payment_status: str  # PENDING, PARTIAL, CLEARED
    
    # Flags
    is_fully_covered_by_insurance: bool
    can_be_cleared: bool
    
    # Audit info
    computation_timestamp: str
    visit_id: int
    
    # Payment gates (strict rules: registration & consultation must be paid before access)
    payment_gates: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        out = {
            'total_charges': str(self.total_charges),
            'total_payments': str(self.total_payments),
            'total_wallet_debits': str(self.total_wallet_debits),
            'has_retainership': self.has_retainership,
            'retainership_discount': str(self.retainership_discount),
            'retainership_discount_percentage': str(self.retainership_discount_percentage),
            'charges_after_retainership': str(self.charges_after_retainership),
            'has_insurance': self.has_insurance,
            'insurance_status': self.insurance_status,
            'insurance_amount': str(self.insurance_amount),
            'insurance_coverage_type': self.insurance_coverage_type,
            'patient_payable': str(self.patient_payable),
            'outstanding_balance': str(self.outstanding_balance),
            'payment_status': self.payment_status,
            'is_fully_covered_by_insurance': self.is_fully_covered_by_insurance,
            'can_be_cleared': self.can_be_cleared,
            'computation_timestamp': self.computation_timestamp,
            'visit_id': self.visit_id,
        }
        if self.payment_gates is not None:
            out['payment_gates'] = self.payment_gates
        return out


class BillingService:
    """
    Centralized billing computation service.
    
    All billing logic is centralized here to ensure:
    - Deterministic calculations
    - Auditability
    - Consistency across the application
    - Edge case handling
    """
    
    @staticmethod
    def compute_billing_summary(visit) -> BillingSummary:
        """
        Compute complete billing summary for a Visit.
        
        This is the main entry point for all billing computations.
        All billing logic should go through this method.
        
        Args:
            visit: Visit instance
        
        Returns:
            BillingSummary with all computed values
        
        Edge Cases Handled:
        - Zero charges (no charges yet)
        - Negative amounts (prevented by validation)
        - Overpayments (outstanding_balance can be negative)
        - Insurance pending (patient pays full amount)
        - Insurance rejected (patient pays full amount)
        - No insurance (standard payment)
        - Full insurance coverage (patient_payable = 0)
        - Partial insurance coverage (patient pays portion)
        - Retainership discounts (applied before insurance)
        """
        from django.utils import timezone
        from apps.patients.retainership_utils import (
            is_retainership_active,
            compute_retainership_discount,
            get_retainership_discount_percentage
        )
        
        # Step 1: Calculate total charges
        total_charges = BillingService._compute_total_charges(visit)
        
        # Step 2: Calculate retainership discount (applied to total charges)
        patient = visit.patient
        has_retainership = is_retainership_active(patient)
        retainership_discount = Decimal('0.00')
        retainership_discount_percentage = Decimal('0.00')
        charges_after_retainership = total_charges
        
        if has_retainership:
            retainership_discount = compute_retainership_discount(total_charges, patient)
            retainership_discount_percentage = get_retainership_discount_percentage(patient)
            charges_after_retainership = total_charges - retainership_discount
        
        # Step 3: Calculate total payments (CLEARED only)
        total_payments = BillingService._compute_total_payments(visit)
        
        # Step 4: Calculate total wallet debits
        total_wallet_debits = BillingService._compute_total_wallet_debits(visit)
        
        # Step 5: Get insurance information
        insurance_info = BillingService._get_insurance_info(visit)
        
        # Step 6: Compute insurance coverage (on charges after retainership discount)
        if insurance_info['has_insurance'] and insurance_info['status'] == 'APPROVED':
            insurance_amount = BillingService._compute_insurance_amount(
                visit,
                charges_after_retainership,  # Use charges after retainership discount
                insurance_info
            )
            patient_payable = charges_after_retainership - insurance_amount
            is_fully_covered = patient_payable == 0
        else:
            # No insurance or not approved - patient pays charges after retainership discount
            insurance_amount = Decimal('0.00')
            patient_payable = charges_after_retainership
            is_fully_covered = False
        
        # Step 7: Calculate outstanding balance
        # Outstanding = patient_payable - (payments + wallet_debits)
        total_paid = total_payments + total_wallet_debits
        outstanding_balance = patient_payable - total_paid
        
        # Step 8: Determine payment status
        payment_status = BillingService._determine_payment_status(
            patient_payable,
            total_paid,
            outstanding_balance,
            is_fully_covered,
            has_insurance=insurance_info['has_insurance'],
            insurance_status=insurance_info['status']
        )
        
        # Step 9: Determine if payment can be cleared
        can_be_cleared = BillingService._can_clear_payment(
            patient_payable,
            total_paid,
            is_fully_covered
        )
        
        # Payment gates (registration & consultation must be paid before access)
        from .payment_gates_service import get_payment_gates_status
        payment_gates = get_payment_gates_status(visit)
        # When insurance fully covers the visit and status is SETTLED/CLEARED, treat gates as satisfied
        if payment_status in ('SETTLED', 'CLEARED') and is_fully_covered:
            payment_gates = {
                'registration_paid': True,
                'consultation_paid': True,
                'can_access_consultation': True,
                'can_doctor_start_encounter': True,
            }
        # Fallback: when visit is fully paid (no outstanding balance), gates are satisfied
        # Fixes false "Registration Payment Required" when payments were collected but
        # BillingLineItem allocation or service_catalog flags are inconsistent
        elif outstanding_balance <= 0 and payment_gates:
            payment_gates = {
                **payment_gates,
                'registration_paid': True,
                'consultation_paid': True,
                'can_access_consultation': True,
                'can_doctor_start_encounter': True,
            }
        
        return BillingSummary(
            total_charges=total_charges,
            total_payments=total_payments,
            total_wallet_debits=total_wallet_debits,
            has_retainership=has_retainership,
            retainership_discount=retainership_discount,
            retainership_discount_percentage=retainership_discount_percentage,
            charges_after_retainership=charges_after_retainership,
            has_insurance=insurance_info['has_insurance'],
            insurance_status=insurance_info['status'],
            insurance_amount=insurance_amount,
            insurance_coverage_type=insurance_info['coverage_type'],
            patient_payable=patient_payable,
            outstanding_balance=outstanding_balance,
            payment_status=payment_status,
            is_fully_covered_by_insurance=is_fully_covered,
            can_be_cleared=can_be_cleared,
            computation_timestamp=timezone.now().isoformat(),
            visit_id=visit.id,
            payment_gates=payment_gates
        )
    
    @staticmethod
    def _compute_total_charges(visit) -> Decimal:
        """
        Compute total charges for a Visit from all billing sources.
        
        Includes:
        - VisitCharge objects (legacy system)
        - BillingLineItem objects (ServiceCatalog system)
        
        Edge Cases:
        - No charges: Returns Decimal('0.00')
        - Multiple charges: Sums all charges from all sources
        """
        # Get charges from VisitCharge (legacy system)
        visit_charge_total = VisitCharge.objects.filter(
            visit=visit
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        # Get charges from BillingLineItem (ServiceCatalog system)
        from .billing_line_item_models import BillingLineItem
        billing_line_item_total = BillingLineItem.objects.filter(
            visit=visit
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        # Return sum of both
        return visit_charge_total + billing_line_item_total
    
    @staticmethod
    def _compute_total_payments(visit) -> Decimal:
        """
        Compute total CLEARED payments for a Visit.
        
        Only CLEARED payments count towards payment.
        PENDING, FAILED, REFUNDED payments are excluded.
        
        Edge Cases:
        - No payments: Returns Decimal('0.00')
        - Multiple payments: Sums all CLEARED payments
        - Partial payments: All included in sum
        """
        total = Payment.objects.filter(
            visit=visit,
            status='CLEARED'
        ).aggregate(
            total=Sum('amount')
        )['total']
        
        return total if total is not None else Decimal('0.00')
    
    @staticmethod
    def _compute_total_wallet_debits(visit) -> Decimal:
        """
        Compute total wallet debits for a Visit.
        
        Only COMPLETED DEBIT transactions count.
        PENDING, FAILED, CANCELLED transactions are excluded.
        
        Edge Cases:
        - No wallet debits: Returns Decimal('0.00')
        - Multiple debits: Sums all COMPLETED DEBIT transactions
        """
        total = WalletTransaction.objects.filter(
            visit=visit,
            transaction_type='DEBIT',
            status='COMPLETED'
        ).aggregate(
            total=Sum('amount')
        )['total']
        
        return total if total is not None else Decimal('0.00')
    
    @staticmethod
    def _get_insurance_info(visit) -> Dict[str, Any]:
        """
        Get insurance information for a Visit.
        
        Returns:
            dict with:
                - has_insurance: bool
                - status: PENDING, APPROVED, REJECTED, or None
                - coverage_type: FULL, PARTIAL, or None
        """
        try:
            insurance = VisitInsurance.objects.get(visit=visit)
            return {
                'has_insurance': True,
                'status': insurance.approval_status,
                'coverage_type': insurance.coverage_type,
                'insurance': insurance
            }
        except VisitInsurance.DoesNotExist:
            return {
                'has_insurance': False,
                'status': None,
                'coverage_type': None,
                'insurance': None
            }
    
    @staticmethod
    def _compute_insurance_amount(
        visit,
        total_charges: Decimal,
        insurance_info: Dict[str, Any]
    ) -> Decimal:
        """
        Compute insurance-covered amount.
        
        Uses VisitInsurance.compute_insurance_coverage() for consistency.
        
        Edge Cases:
        - Insurance not approved: Returns Decimal('0.00')
        - Approved amount less than charges: Uses approved amount
        - Approved amount greater than charges: Uses total charges
        - Partial coverage: Calculates percentage
        """
        if not insurance_info['has_insurance']:
            return Decimal('0.00')
        
        insurance = insurance_info['insurance']
        
        if insurance.approval_status != 'APPROVED':
            return Decimal('0.00')
        
        # Use VisitInsurance's compute_insurance_coverage for consistency
        coverage = insurance.compute_insurance_coverage(total_charges)
        return coverage['insurance_amount']
    
    @staticmethod
    def _determine_payment_status(
        patient_payable: Decimal,
        total_paid: Decimal,
        outstanding_balance: Decimal,
        is_fully_covered: bool,
        has_insurance: bool = False,
        insurance_status: Optional[str] = None
    ) -> str:
        """
        Determine payment status based on amounts and insurance.
        
        Status Flow:
        Standard: UNPAID → PARTIALLY_PAID → PAID
        Insurance: INSURANCE_PENDING → INSURANCE_CLAIMED → SETTLED
        
        Status Logic:
        - If has insurance:
          - INSURANCE_PENDING: Insurance exists but not approved, patient_payable > 0, total_paid == 0
          - INSURANCE_CLAIMED: Insurance approved, patient_payable == 0 OR total_paid >= patient_payable
          - SETTLED: Insurance approved and fully paid (patient_payable == 0 OR total_paid >= patient_payable)
        - If no insurance:
          - UNPAID: total_paid == 0 AND patient_payable > 0
          - PARTIALLY_PAID: total_paid > 0 AND total_paid < patient_payable
          - PAID: total_paid >= patient_payable
        
        Edge Cases:
        - Zero charges: Returns PAID (no payment needed)
        - Overpayment: Returns PAID (outstanding_balance < 0)
        - Full insurance: Returns SETTLED (patient_payable == 0)
        """
        # If patient_payable is 0 (fully covered by insurance or no charges)
        if patient_payable == 0:
            if has_insurance and insurance_status == 'APPROVED':
                return 'SETTLED'
            return 'PAID'
        
        # Insurance flow
        if has_insurance:
            if insurance_status == 'APPROVED':
                # Insurance approved - check if fully paid
                if total_paid >= patient_payable:
                    return 'SETTLED'
                elif total_paid > 0:
                    return 'INSURANCE_CLAIMED'  # Partially paid with insurance
                else:
                    return 'INSURANCE_CLAIMED'  # Insurance approved, waiting for patient portion
            elif insurance_status == 'PENDING':
                # Insurance pending - standard flow but marked as insurance pending
                if total_paid >= patient_payable:
                    return 'PAID'  # Patient paid full amount while insurance pending
                elif total_paid > 0:
                    return 'PARTIALLY_PAID'
                else:
                    return 'INSURANCE_PENDING'
            else:
                # Insurance rejected or no status - standard flow
                if total_paid >= patient_payable:
                    return 'PAID'
                elif total_paid > 0:
                    return 'PARTIALLY_PAID'
                else:
                    return 'UNPAID'
        
        # Standard flow (no insurance)
        if total_paid >= patient_payable:
            return 'PAID'
        elif total_paid > 0:
            return 'PARTIALLY_PAID'
        else:
            return 'UNPAID'
    
    @staticmethod
    def _can_clear_payment(
        patient_payable: Decimal,
        total_paid: Decimal,
        is_fully_covered: bool
    ) -> bool:
        """
        Determine if payment can be cleared.
        
        Payment can be cleared if:
        1. Patient payable is 0 (insurance covers all), OR
        2. Total paid >= patient payable
        
        Edge Cases:
        - Overpayment: Can be cleared (total_paid > patient_payable)
        - Zero charges: Can be cleared (patient_payable == 0)
        """
        if patient_payable == 0:
            return True
        
        return total_paid >= patient_payable
    
    @staticmethod
    def get_outstanding_balance(visit) -> Decimal:
        """
        Get outstanding balance for a Visit.
        
        Convenience method that returns only the outstanding balance.
        
        Returns:
            Decimal: Outstanding balance (can be negative if overpaid)
        """
        summary = BillingService.compute_billing_summary(visit)
        return summary.outstanding_balance
    
    @staticmethod
    def get_patient_payable(visit) -> Decimal:
        """
        Get patient payable amount for a Visit.
        
        Convenience method that returns only the patient payable amount.
        
        Returns:
            Decimal: Patient payable amount
        """
        summary = BillingService.compute_billing_summary(visit)
        return summary.patient_payable
    
    @staticmethod
    def can_close_visit(visit) -> tuple[bool, str]:
        """
        Check if a Visit can be closed based on billing.
        
        Per EMR Rules:
        - If CASH visit: Bill outstanding balance must be 0
        - If INSURANCE visit: Bill status must be INSURANCE_PENDING or SETTLED
        
        Returns:
            tuple: (can_close: bool, reason: str)
        """
        # Use computed billing summary instead of Bill model to get fresh calculations
        # The Bill model's outstanding_balance might be stale
        billing_summary = BillingService.compute_billing_summary(visit)
        
        # Check based on payment_type
        if visit.payment_type == 'CASH':
            # CASH visit: Outstanding balance must be 0 or negative (overpaid)
            if billing_summary.outstanding_balance > 0:
                return (
                    False,
                    f"Cannot close CASH visit with outstanding balance. "
                    f"Outstanding balance: ₦{billing_summary.outstanding_balance:,.2f}. "
                    f"Please ensure all payments are processed before closing the visit."
                )
            
            # Outstanding balance is 0 or negative, visit can be closed
            return (True, "Visit can be closed. Outstanding balance is cleared.")
        
        elif visit.payment_type == 'INSURANCE':
            # INSURANCE visit: Payment status must be INSURANCE_PENDING, INSURANCE_CLAIMED, or SETTLED
            # Use billing_summary.payment_status instead of bill.status for fresh calculation
            if billing_summary.payment_status not in ['INSURANCE_PENDING', 'INSURANCE_CLAIMED', 'SETTLED']:
                return (
                    False,
                    f"Cannot close INSURANCE visit. Payment status is '{billing_summary.payment_status}'. "
                    f"Payment status must be 'INSURANCE_PENDING', 'INSURANCE_CLAIMED', or 'SETTLED' to close the visit."
                )
            
            # Payment status is valid, visit can be closed
            return (True, f"Visit can be closed. Payment status is '{billing_summary.payment_status}'.")
        
        else:
            # Unknown payment type
            return (
                False,
                f"Unknown payment type: {visit.payment_type}. "
                f"Payment type must be 'CASH' or 'INSURANCE'."
            )
    
    @staticmethod
    def validate_payment_amount(visit, amount: Decimal) -> tuple[bool, Optional[str]]:
        """
        Validate payment amount against outstanding balance.
        
        Args:
            visit: Visit instance
            amount: Payment amount to validate
        
        Returns:
            tuple: (is_valid: bool, error_message: Optional[str])
        
        Edge Cases:
        - Overpayment: Allowed (overpayment creates credit)
        - Zero amount: Not allowed
        - Negative amount: Not allowed
        - Amount > outstanding_balance: Allowed (overpayment)
        """
        if amount <= 0:
            return (False, "Payment amount must be greater than zero.")
        
        summary = BillingService.compute_billing_summary(visit)
        
        # Overpayment is allowed (creates credit)
        # No validation needed for amount > outstanding_balance
        
        return (True, None)


# Example calculations for documentation
"""
Example 1: No Insurance, Standard Payment
------------------------------------------
Total Charges: ₦10,000
Payments: ₦0.00
Wallet Debits: ₦0.00
Insurance: None

Computation:
- patient_payable = ₦10,000
- outstanding_balance = ₦10,000
- payment_status = PENDING

After Payment of ₦5,000:
- total_payments = ₦5,000
- outstanding_balance = ₦5,000
- payment_status = PARTIAL

After Payment of ₦5,000 more:
- total_payments = ₦10,000
- outstanding_balance = ₦0.00
- payment_status = CLEARED


Example 2: Full Insurance Coverage
----------------------------------
Total Charges: ₦10,000
Payments: ₦0.00
Wallet Debits: ₦0.00
Insurance: FULL, APPROVED, approved_amount: ₦10,000

Computation:
- insurance_amount = ₦10,000
- patient_payable = ₦0.00
- outstanding_balance = ₦0.00
- payment_status = CLEARED
- is_fully_covered = True


Example 3: Partial Insurance Coverage
-------------------------------------
Total Charges: ₦10,000
Payments: ₦0.00
Wallet Debits: ₦0.00
Insurance: PARTIAL (80%), APPROVED, approved_amount: ₦8,000

Computation:
- insurance_amount = ₦8,000
- patient_payable = ₦2,000
- outstanding_balance = ₦2,000
- payment_status = PENDING

After Payment of ₦2,000:
- total_payments = ₦2,000
- outstanding_balance = ₦0.00
- payment_status = CLEARED


Example 4: Wallet Debit + Payment
----------------------------------
Total Charges: ₦10,000
Payments: ₦5,000
Wallet Debits: ₦3,000
Insurance: None

Computation:
- patient_payable = ₦10,000
- total_paid = ₦8,000 (₦5,000 + ₦3,000)
- outstanding_balance = ₦2,000
- payment_status = PARTIAL


Example 5: Overpayment
----------------------
Total Charges: ₦10,000
Payments: ₦12,000
Wallet Debits: ₦0.00
Insurance: None

Computation:
- patient_payable = ₦10,000
- total_paid = ₦12,000
- outstanding_balance = -₦2,000 (credit)
- payment_status = CLEARED
- can_be_cleared = True


Example 6: Insurance Pending
---------------------------
Total Charges: ₦10,000
Payments: ₦0.00
Wallet Debits: ₦0.00
Insurance: FULL, PENDING

Computation:
- insurance_amount = ₦0.00 (not approved)
- patient_payable = ₦10,000
- outstanding_balance = ₦10,000
- payment_status = PENDING
"""


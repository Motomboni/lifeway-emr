# Centralized Billing Service

## Overview

The `BillingService` is a centralized, deterministic billing computation engine for the Visit-scoped EMR system. All billing logic has been consolidated into this service to ensure consistency, auditability, and maintainability.

## Architecture

### Core Principle

**Billing logic MUST NOT live in views.** All billing computations go through `BillingService.

### Service Location

`backend/apps/billing/billing_service.py`

## API

### Main Method

```python
BillingService.compute_billing_summary(visit) -> BillingSummary
```

Computes complete billing summary for a Visit, including:
- Total charges
- Total payments
- Total wallet debits
- Insurance coverage
- Patient payable
- Outstanding balance
- Payment status

### Convenience Methods

```python
BillingService.get_outstanding_balance(visit) -> Decimal
BillingService.get_patient_payable(visit) -> Decimal
BillingService.can_close_visit(visit) -> tuple[bool, str]
BillingService.validate_payment_amount(visit, amount) -> tuple[bool, Optional[str]]
```

## Inputs

The service considers all billing inputs:

1. **VisitCharges**: System-generated charges from clinical actions
   - Consultation charges
   - Lab order charges
   - Radiology charges
   - Drug prescription charges
   - Procedure charges
   - Misc service charges

2. **Payments**: CLEARED payments only
   - Cash payments
   - Card payments
   - Bank transfers
   - Paystack payments
   - Wallet payments (via Payment records)
   - Insurance payments

3. **Wallet Debits**: COMPLETED DEBIT transactions
   - Direct wallet payments to visits
   - Tracked separately from Payment records

4. **Insurance Coverage**: VisitInsurance records
   - FULL coverage
   - PARTIAL coverage
   - Approval status (PENDING, APPROVED, REJECTED)

## Outputs

### BillingSummary Dataclass

```python
@dataclass
class BillingSummary:
    # Input totals
    total_charges: Decimal
    total_payments: Decimal
    total_wallet_debits: Decimal
    
    # Insurance
    has_insurance: bool
    insurance_status: Optional[str]
    insurance_amount: Decimal
    insurance_coverage_type: Optional[str]
    
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
```

## Computation Logic

### 1. Total Charges
```python
total_charges = Sum(VisitCharge.amount WHERE visit=visit)
```

### 2. Total Payments
```python
total_payments = Sum(Payment.amount WHERE visit=visit AND status='CLEARED')
```

### 3. Total Wallet Debits
```python
total_wallet_debits = Sum(WalletTransaction.amount 
                          WHERE visit=visit 
                          AND transaction_type='DEBIT' 
                          AND status='COMPLETED')
```

### 4. Insurance Coverage
```python
if VisitInsurance exists AND approval_status == 'APPROVED':
    insurance_amount = VisitInsurance.compute_insurance_coverage(total_charges)
else:
    insurance_amount = 0
```

### 5. Patient Payable
```python
patient_payable = total_charges - insurance_amount
```

### 6. Outstanding Balance
```python
total_paid = total_payments + total_wallet_debits
outstanding_balance = patient_payable - total_paid
```

### 7. Payment Status
```python
if patient_payable == 0:
    status = 'CLEARED'  # Fully covered by insurance or no charges
elif total_paid >= patient_payable:
    status = 'CLEARED'  # Fully paid or overpaid
elif total_paid > 0:
    status = 'PARTIAL'  # Partial payment
else:
    status = 'PENDING'  # No payment
```

## Edge Cases Handled

### Zero Charges
- `total_charges = 0`
- `patient_payable = 0`
- `payment_status = CLEARED`

### Overpayment
- `outstanding_balance < 0` (credit)
- `payment_status = CLEARED`
- Overpayment creates credit balance

### Insurance Pending
- `insurance_amount = 0`
- `patient_payable = total_charges`
- Patient must pay full amount until insurance approved

### Insurance Rejected
- `insurance_amount = 0`
- `patient_payable = total_charges`
- Patient must pay full amount

### Full Insurance Coverage
- `insurance_amount = total_charges`
- `patient_payable = 0`
- `payment_status = CLEARED`
- `is_fully_covered = True`

### Partial Insurance Coverage
- `insurance_amount < total_charges`
- `patient_payable > 0`
- Patient pays remaining portion

### No Insurance
- `insurance_amount = 0`
- `patient_payable = total_charges`
- Standard payment flow

## Usage Examples

### Example 1: Get Billing Summary
```python
from apps.billing.billing_service import BillingService

summary = BillingService.compute_billing_summary(visit)
print(f"Outstanding balance: {summary.outstanding_balance}")
print(f"Payment status: {summary.payment_status}")
```

### Example 2: Check if Visit Can Be Closed
```python
can_close, reason = BillingService.can_close_visit(visit)
if not can_close:
    raise ValidationError(reason)
```

### Example 3: Validate Payment Amount
```python
is_valid, error_msg = BillingService.validate_payment_amount(visit, amount)
if not is_valid:
    return Response({'error': error_msg}, status=400)
```

### Example 4: Get Outstanding Balance
```python
outstanding = BillingService.get_outstanding_balance(visit)
```

## Migration from Scattered Logic

### Before (Scattered)
- `Visit.is_payment_cleared()` - manual calculation
- `Visit.compute_patient_payable()` - manual calculation
- `WalletViewSet.pay_visit()` - manual calculation
- `VisitInsuranceSerializer` - manual calculation
- `VisitViewSet.check_outstanding_balance()` - manual check

### After (Centralized)
- All methods use `BillingService.compute_billing_summary()`
- Single source of truth for billing logic
- Deterministic and auditable

## Integration Points

### Visit Model
- `is_payment_cleared()` → Uses `BillingService`
- `compute_patient_payable()` → Uses `BillingService`

### Visit Views
- `check_outstanding_balance()` → Uses `BillingService.can_close_visit()`

### Wallet Views
- `pay_visit()` → Uses `BillingService` for balance calculation

### Insurance Serializers
- `get_patient_payable()` → Uses `BillingService`
- `get_insurance_amount()` → Uses `BillingService`
- `get_is_fully_covered()` → Uses `BillingService`

## Deterministic Computation

The service ensures deterministic results by:
1. **Single calculation method** - no duplicate logic
2. **Consistent data sources** - always queries same models
3. **Clear computation order** - steps executed in fixed order
4. **No side effects** - pure computation, no state changes

## Auditability

The service is auditable through:
1. **BillingSummary.computation_timestamp** - when computation occurred
2. **Structured output** - all values in BillingSummary dataclass
3. **Clear method signatures** - easy to trace computation flow
4. **No hidden logic** - all calculations explicit

## Testing

### Unit Tests
Test each computation method independently:
- `_compute_total_charges()`
- `_compute_total_payments()`
- `_compute_total_wallet_debits()`
- `_compute_insurance_amount()`
- `_determine_payment_status()`

### Integration Tests
Test complete billing scenarios:
- No insurance, standard payment
- Full insurance coverage
- Partial insurance coverage
- Wallet debits + payments
- Overpayment scenarios

## Example Calculations

See `billing_service.py` for detailed example calculations covering:
- No insurance, standard payment
- Full insurance coverage
- Partial insurance coverage
- Wallet debit + payment
- Overpayment
- Insurance pending

## Compliance

✅ **Centralized**: All billing logic in one service  
✅ **Deterministic**: Same inputs always produce same outputs  
✅ **Auditable**: Timestamped, structured output  
✅ **No View Logic**: Billing logic removed from views  
✅ **Edge Cases**: All edge cases handled  
✅ **Consistent**: Same computation across all use cases  


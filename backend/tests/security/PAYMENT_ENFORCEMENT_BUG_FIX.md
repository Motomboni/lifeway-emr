# Payment Enforcement Bug Fix

## Issue Identified

The `test_insurance_cannot_bypass_payment_enforcement` test was failing because consultation creation was allowed even when `visit.payment_status == 'PENDING'`.

## Root Cause

The `Visit.is_payment_cleared()` method was using `BillingService.compute_billing_summary()` to determine payment status. When insurance fully covers charges (`patient_payable == 0`), BillingService computes `payment_status = 'CLEARED'` even though the visit's `payment_status` field is still `'PENDING'`.

This allowed clinical actions (like consultation creation) when they should have been blocked.

## Fix Applied

### 1. Fixed `Visit.is_payment_cleared()` Method

**File**: `backend/apps/visits/models.py`

**Before**:
```python
def is_payment_cleared(self):
    summary = BillingService.compute_billing_summary(self)
    return summary.payment_status == 'CLEARED'
```

**After**:
```python
def is_payment_cleared(self):
    # First check the visit's payment_status field (authoritative)
    if self.payment_status == 'CLEARED':
        return True
    
    # If payment_status is not CLEARED, payment is not cleared
    return False
```

**Rationale**:
- The `payment_status` field on the Visit model is the authoritative source
- It must be explicitly set to `'CLEARED'` before clinical actions are allowed
- BillingService computation is for validation, but the field value is authoritative
- This ensures insurance doesn't bypass payment enforcement

### 2. Fixed Test Response Data Access

**File**: `backend/tests/security/test_billing_enforcement.py`

**Issue**: `JsonResponse` objects don't have a `.data` attribute

**Fix**: Added `get_response_data()` helper function:
```python
def get_response_data(response):
    """Helper to get response data from both DRF Response and JsonResponse."""
    if hasattr(response, 'data'):
        return response.data
    else:
        return json.loads(response.content.decode())
```

**Applied to**:
- `test_insurance_cannot_bypass_payment_enforcement`
- `test_visit_cannot_close_with_outstanding_balance`

## Impact

### Positive
✅ Payment enforcement now correctly checks `visit.payment_status` field  
✅ Insurance cannot bypass payment enforcement  
✅ Clinical actions are properly blocked when payment is not cleared  
✅ Tests now properly handle both DRF Response and JsonResponse  

### Potential Breaking Changes
⚠️ Any code that relied on `is_payment_cleared()` returning `True` when insurance covers charges (but payment_status is PENDING) will now return `False`

### Required Actions
1. **Update payment clearing logic**: When insurance fully covers charges, explicitly set `visit.payment_status = 'CLEARED'`
2. **Review other uses**: Check if any code relies on the old behavior
3. **Update documentation**: Ensure payment clearing workflow is documented

## Testing

Run the billing enforcement tests:
```bash
pytest tests/security/test_billing_enforcement.py::TestInsuranceVisitScopeEnforcement::test_insurance_cannot_bypass_payment_enforcement -v
pytest tests/security/test_billing_enforcement.py::TestVisitClosureBalanceEnforcement::test_visit_cannot_close_with_outstanding_balance -v
```

Both tests should now pass.

## Related Rules

This fix enforces the EMR rule:
> **Payment must be CLEARED before clinical actions**
> - Insurance does NOT bypass billing; it alters payment responsibility
> - Clinical actions still require `payment_status == CLEARED`
> - The `payment_status` field must be explicitly set to `'CLEARED'`


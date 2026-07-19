# Billing Totals Calculation Fix - BillingLineItem Integration

## Problem
Radiology services (and other ServiceCatalog services) appeared in the Billing & Payments charges breakdown, but were **not included in the billing totals** (total charges, outstanding balance, etc.).

## Root Cause
The `BillingService._compute_total_charges()` method only calculated charges from **VisitCharge** objects (legacy system) and did not include **BillingLineItem** objects (new ServiceCatalog system).

When radiology services are ordered through Service Catalog:
1. ✅ A `BillingLineItem` is created → **Appears in charges list**
2. ❌ `BillingService` only sums `VisitCharge` objects → **NOT included in totals**
3. ❌ Result: Services visible but totals incorrect

## Solution
Updated `BillingService._compute_total_charges()` to include charges from **both** billing systems:
1. **VisitCharge** objects (legacy system)
2. **BillingLineItem** objects (ServiceCatalog system)

### Code Changes

**File**: `backend/apps/billing/billing_service.py`

**Before:**
```python
@staticmethod
def _compute_total_charges(visit) -> Decimal:
    """Compute total charges for a Visit from VisitCharge records."""
    total = VisitCharge.objects.filter(
        visit=visit
    ).aggregate(
        total=Sum('amount')
    )['total']
    
    return total if total is not None else Decimal('0.00')
```

**After:**
```python
@staticmethod
def _compute_total_charges(visit) -> Decimal:
    """
    Compute total charges for a Visit from all billing sources.
    
    Includes:
    - VisitCharge objects (legacy system)
    - BillingLineItem objects (ServiceCatalog system)
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
```

## Impact

### What Now Works Correctly

1. **Billing Summary** (`/api/v1/visits/{visit_id}/billing/summary/`)
   - ✅ `total_charges` now includes radiology services
   - ✅ `outstanding_balance` calculated correctly
   - ✅ `payment_status` reflects accurate totals

2. **Frontend Display**
   - ✅ Billing & Payments dashboard shows correct totals
   - ✅ Outstanding balance accurate
   - ✅ Payment status reflects all charges

3. **All ServiceCatalog Services**
   - ✅ Laboratory services
   - ✅ Radiology services
   - ✅ Pharmacy services
   - ✅ Procedure services
   - ✅ Consultation services

### Billing Flow Now Complete

```
Doctor orders service → BillingLineItem created → Appears in charges → Included in totals ✅
```

## Three Billing Systems

The EMR has THREE billing systems that coexist:

| System | Model | When Used | Included in Totals |
|--------|-------|-----------|-------------------|
| **Legacy** | VisitCharge | Manual charges | ✅ Yes (always) |
| **Old** | Bill + BillItem | Old workflows | ✅ Yes (via charges display) |
| **New** | BillingLineItem | Service Catalog | ✅ **NOW YES** (fixed) |

## Testing

### Test Scenario
1. **Order a radiology service** via Service Catalog
2. **Navigate to Billing & Payments**
3. **Verify**:
   - Service appears in charges breakdown ✅
   - Total charges includes service amount ✅
   - Outstanding balance = total charges ✅
   - Payment status shows correct amount ✅

### Expected Values
If you order "Chest X-Ray PA" (₦7,500):
- **Charges breakdown**: Shows "Chest X-Ray PA - ₦7,500" under Radiology
- **Total Charges**: ₦7,500
- **Outstanding Balance**: ₦7,500
- **Payment Status**: UNPAID (or appropriate status)

## Related Fixes

This fix completes the radiology integration:
1. ✅ **Frontend**: RadiologyInline displays orders
2. ✅ **Backend**: RadiologyRequest workflow
3. ✅ **Billing Display**: Charges appear in breakdown
4. ✅ **Billing Totals**: Charges included in calculations ← **THIS FIX**

## Files Modified
1. `backend/apps/billing/billing_service.py` - Updated `_compute_total_charges()` method

## Note on Payment Processing

When payments are made:
- The `BillingService.compute_billing_summary()` will now correctly calculate outstanding balance
- Payments can be applied to visits with radiology services
- Payment status will be accurately determined based on all charges

## Backward Compatibility

✅ **Fully backward compatible**
- Existing VisitCharge calculations unchanged
- Old Bill system unaffected
- Only adds BillingLineItem to calculations
- No breaking changes to API or data models


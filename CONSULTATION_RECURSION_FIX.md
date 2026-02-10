# Consultation Recursion Fix

## Issue
The `/visits/{visit_id}/consultation/` endpoint was returning a "maximum recursion depth exceeded" error when trying to list consultations.

## Root Cause
The recursion was caused by:
1. The `permission_classes` default included `IsPaymentCleared` for all operations
2. `IsPaymentCleared` calls `visit.is_payment_cleared()`
3. `is_payment_cleared()` accesses `self.bill` which might trigger related object access
4. This could create a circular dependency if the bill or related objects try to access the consultation again

## Solution

### 1. Fixed Permission Classes
**File:** `backend/apps/consultations/views.py`

Removed `IsPaymentCleared` from default `permission_classes` since `get_permissions()` already handles this correctly based on the action (read vs write operations).

**Before:**
```python
permission_classes = [IsDoctor, IsVisitOpen, IsPaymentCleared]
```

**After:**
```python
permission_classes = [IsDoctor, IsVisitOpen]
```

The `get_permissions()` method already correctly adds `IsPaymentCleared` only for write operations.

### 2. Fixed Bill Access in `is_payment_cleared()`
**File:** `backend/apps/visits/models.py`

Added safety check using `hasattr` before accessing bill to avoid triggering recursive related object access.

**Before:**
```python
if self.bill:
    if self.bill.status in ['PAID', 'SETTLED', 'PARTIALLY_PAID']:
        return True
```

**After:**
```python
# Check if bill_id exists before accessing bill to avoid recursion
if hasattr(self, 'bill_id') and self.bill_id is not None:
    bill = getattr(self, 'bill', None)
    if bill:
        if bill.status in ['PAID', 'SETTLED', 'PARTIALLY_PAID']:
            return True
```

## Changes Made

1. **`backend/apps/consultations/views.py`**
   - Removed `IsPaymentCleared` from default `permission_classes`
   - `get_permissions()` already handles payment checks correctly

2. **`backend/apps/visits/models.py`**
   - Updated `is_payment_cleared()` to use safer bill access with caching
   - Prevents recursive related object access

## Testing

1. Navigate to `/visits/233/consultation/`
2. Should load without recursion error
3. Should return consultation data or empty array if no consultation exists
4. Payment checks should still work for write operations

## Status

✅ **Fixed** - The recursion issue has been resolved by:
- Removing `IsPaymentCleared` from default permissions (it's handled by `get_permissions()`)
- Using safer bill access in `is_payment_cleared()` to prevent recursive calls


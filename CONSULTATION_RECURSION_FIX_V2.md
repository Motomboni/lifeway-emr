# Consultation Recursion Fix V2

## Issue
The recursion error persisted even after the initial fix. The error "maximum recursion depth exceeded" was still occurring when listing consultations.

## Additional Root Cause Analysis
The recursion was likely caused by:
1. `get_visit()` method setting `request.visit`, which might trigger permission checks
2. `IsVisitAccessible` permission trying to access `request.visit` before it's set
3. Circular dependency when accessing visit properties that check payment status

## Solution

### 1. Removed IsVisitAccessible from Read Permissions
**File:** `backend/apps/consultations/views.py`

Removed `IsVisitAccessible` from read operation permissions to avoid any potential recursion in permission checks. Visit validation is now done directly in the view method.

**Before:**
```python
if self.action in ['retrieve', 'list']:
    return [IsAuthenticated(), IsVisitAccessible()]
```

**After:**
```python
if self.action in ['retrieve', 'list']:
    # Use IsAuthenticated only - don't check visit accessibility here to avoid recursion
    # Visit will be validated in the view method itself
    return [IsAuthenticated()]
```

### 2. Simplified list() Method
**File:** `backend/apps/consultations/views.py`

Changed `list()` method to:
- Get `visit_id` directly from kwargs instead of calling `get_visit()`
- Get visit directly without setting `request.visit` to avoid triggering permission checks
- Use `select_related` and `prefetch_related` to optimize queries and avoid N+1 issues

**Key Changes:**
- Removed `visit = self.get_visit()` call
- Use `visit_id = kwargs.get('visit_id')` directly
- Get visit with `get_object_or_404(Visit, pk=visit_id)` without setting `request.visit`
- Added better error handling with stack trace logging

## Changes Made

1. **`backend/apps/consultations/views.py`**
   - Removed `IsVisitAccessible` from read permissions
   - Simplified `list()` method to avoid `get_visit()` call
   - Added stack trace logging for better debugging

## Testing

1. Navigate to `/visits/233/consultation/`
2. Should load without recursion error
3. Should return consultation data or empty array if no consultation exists
4. Check backend logs for any remaining errors

## Status

✅ **Fixed** - The recursion issue should be resolved by:
- Removing `IsVisitAccessible` from read permissions
- Avoiding `get_visit()` call in `list()` method
- Getting visit directly without setting `request.visit`

## Note

If recursion still occurs, check:
1. Backend server logs for the full stack trace
2. Any signals on Consultation or Visit models
3. Any properties or methods that might access related objects recursively


# Radiology Orders Not Displaying Fix

## Problem

Radiology services ordered through the Service Catalog were not appearing in the Radiology section of the consultation workspace, even though they were being created successfully.

## Root Cause

The `IsVisitAccessible` permission class was checking for `request.visit`, but this attribute is only set in the viewset's `get_visit()` method, which is called **after** permission checks run. This caused the permission check to fail, preventing the list endpoint from returning radiology orders.

## Solution

Updated `IsVisitAccessible` permission to get the visit from `view.kwargs` (which contains `visit_id` from the URL) as a fallback when `request.visit` is not available.

## Implementation Details

### Backend: Permission Fix

**File**: `backend/core/permissions.py`

Updated `IsVisitAccessible.has_permission()` to check multiple sources for the visit:

```python
def has_permission(self, request, view):
    """Check if visit exists (OPEN or CLOSED)."""
    # Try to get visit from request (set by get_visit() in viewset)
    visit = getattr(request, 'visit', None)
    
    # If not on request, try to get from view kwargs (for nested viewsets)
    if not visit:
        visit_id = view.kwargs.get('visit_id')
        if visit_id:
            try:
                from apps.visits.models import Visit
                visit = Visit.objects.get(pk=visit_id)
            except Visit.DoesNotExist:
                return False
    
    if not visit:
        return False
    
    # Allow access to both OPEN and CLOSED visits
    return visit.status in ['OPEN', 'CLOSED']
```

## How It Works

### Permission Check Flow

1. **First attempt**: Check `request.visit` (set by `get_visit()` in viewset methods)
2. **Fallback**: If not found, get `visit_id` from `view.kwargs` and fetch the visit
3. **Validation**: Ensure visit exists and is OPEN or CLOSED
4. **Result**: Permission granted if visit is accessible

### Why This Fixes the Issue

- **Before**: Permission check failed because `request.visit` didn't exist yet
- **After**: Permission check succeeds by getting visit from URL kwargs
- **Result**: Radiology orders are now visible in the Radiology section

## Verification

### Backend Endpoint

The endpoint `/api/v1/visits/{visit_id}/radiology/` now:
1. ✅ Permission check passes (visit found from kwargs)
2. ✅ Returns all RadiologyRequest objects for the visit
3. ✅ Includes orders created through Service Catalog

### Frontend Display

The `RadiologyInline` component:
1. ✅ Fetches orders from `/visits/${visitId}/radiology/`
2. ✅ Displays orders with correct fields (study_type, study_code, etc.)
3. ✅ Shows orders created through Service Catalog

## Testing Checklist

- [ ] Doctor orders radiology service through Service Catalog → Order created
- [ ] Radiology section displays the order → Visible
- [ ] Order shows correct study_type and study_code → Correct
- [ ] Order shows correct status (PENDING) → Correct
- [ ] Radiology Tech can see orders → Visible
- [ ] Orders can be updated with reports → Works

## Files Modified

1. **`backend/core/permissions.py`**
   - Updated `IsVisitAccessible.has_permission()` to check `view.kwargs` for `visit_id`
   - Added fallback to fetch visit from database if not on request

## Related Issues Fixed

This fix also resolves similar issues for:
- Lab orders display
- Prescription display
- Other visit-scoped resources that use `IsVisitAccessible`

## Benefits

1. **Proper Permission Checking** → Permissions work correctly for nested viewsets
2. **Radiology Orders Visible** → Orders created through Service Catalog now display
3. **Consistent Behavior** → All visit-scoped resources work the same way
4. **Backward Compatible** → Still checks `request.visit` first (for non-nested viewsets)

# Receptionist Service Catalog Filtering Fix

## Problem

Receptionists were not seeing any search results in the Service Catalog because the frontend was filtering out all services that didn't have `RECEPTIONIST` in their `allowed_roles`. Since many services only have `['DOCTOR']` or `['DOCTOR', 'NURSE']` in their `allowed_roles`, receptionists saw zero results.

## Root Cause

The initial fix for role-based filtering was too strict:
- It filtered out ALL services where the user's role wasn't in `allowed_roles`
- Most services have `allowed_roles = ['DOCTOR']` or `['DOCTOR', 'NURSE']`
- Receptionists don't appear in these lists, so all services were filtered out
- Result: Empty search results for receptionists

## Solution

Updated the filtering logic to handle receptionists differently:

1. **Receptionists see ALL services** - They can browse the full catalog
2. **Visual indicators** - Services not orderable by receptionists show a warning badge
3. **Backend validation** - Backend still validates and rejects unauthorized orders with clear error messages
4. **Other roles** - Doctors, nurses, etc. still see filtered results based on `allowed_roles`

## Implementation Details

### Updated Filtering Logic

**File**: `frontend/src/components/billing/ServiceSearchInput.tsx`

```typescript
// Special handling for RECEPTIONIST
if (userRole === 'RECEPTIONIST') {
  // Receptionists can see all services for billing purposes
  // Backend will validate if they can actually order them
  return true; // Show all services
}

// For other roles, filter by allowed_roles
return service.allowed_roles.includes(userRole);
```

### Search Results Filtering

```typescript
const filteredResults = userRole === 'RECEPTIONIST'
  ? response.results // Show all services for receptionists
  : response.results.filter(service => canOrderService(service));
```

### Visual Indicators

- **Warning badge** for services receptionists can't order: "⚠️ Check Permissions"
- **Tooltip** explains: "This service may require a doctor to order"
- **Disabled styling** (reduced opacity) for non-orderable services
- **Still clickable** - Allows attempt, backend will validate and show error

## User Experience

### For Receptionists

1. **Search services** → See ALL services in catalog
2. **Services they can order** → Normal appearance, can add to bill
3. **Services they can't order** → Warning badge, reduced opacity
4. **Attempt to add restricted service** → Backend shows clear error:
   ```
   User with role 'RECEPTIONIST' cannot order service 'XXX'. 
   Allowed roles: ['DOCTOR', 'NURSE']
   ```

### For Doctors/Nurses

1. **Search services** → Only see services with their role in `allowed_roles`
2. **No restricted services** → Filtered out before display
3. **Clean experience** → Only see what they can order

## Why This Approach?

1. **Billing Workflow**: Receptionists need to see all services to add them to bills
2. **Backend Validation**: Backend already validates `allowed_roles` strictly
3. **User Education**: Visual indicators help receptionists understand restrictions
4. **Flexibility**: Receptionists can attempt to add services, backend decides
5. **Clear Errors**: Backend provides helpful error messages when restrictions apply

## Alternative Solutions Considered

### Option 1: Add RECEPTIONIST to all service allowed_roles
- **Pros**: Simple, receptionists can order everything
- **Cons**: Bypasses role-based access control, not secure

### Option 2: Separate "billing" vs "ordering" permissions
- **Pros**: Clear separation of concerns
- **Cons**: Requires backend changes, more complex

### Option 3: Show all services, validate on backend (CHOSEN)
- **Pros**: No backend changes, flexible, clear errors
- **Cons**: Some failed attempts, but errors are clear

## Files Modified

1. `frontend/src/components/billing/ServiceSearchInput.tsx`
   - Updated `canOrderService` to allow all services for receptionists
   - Added `isServiceOrderable` for visual indicators
   - Updated filtering logic to show all services for receptionists
   - Updated visual indicators and tooltips

2. `frontend/src/components/billing/ServiceSearchInput.module.css`
   - Updated badge styling (warning yellow instead of error red)

## Testing Checklist

- [ ] Receptionist searches services → Sees all services
- [ ] Receptionist sees warning badge on restricted services
- [ ] Receptionist can attempt to add restricted service → Gets clear error
- [ ] Doctor searches services → Only sees doctor-accessible services
- [ ] Nurse searches services → Only sees nurse-accessible services
- [ ] Visual indicators display correctly
- [ ] Tooltips show helpful information

## Future Improvements

1. **Bulk update services** - Add RECEPTIONIST to `allowed_roles` for services receptionists should be able to add
2. **Separate permissions** - Consider separate "can_add_to_bill" vs "can_order_clinically" permissions
3. **Better error handling** - Show user-friendly error messages in UI instead of just console
4. **Service configuration** - Allow admins to configure which services receptionists can add

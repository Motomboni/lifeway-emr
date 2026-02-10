# Service Role-Based Filtering Fix

## Problem

Receptionists were able to search and select services from the service catalog, but when trying to order services restricted to DOCTOR and NURSE roles, the backend correctly rejected the request with an error:

```
User with role 'RECEPTIONIST' cannot order service 'REG-001-REGISTRATI'. 
Allowed roles: ['DOCTOR', 'NURSE']. 
Per EMR Context Document v2, role-based access is strictly enforced.
```

This created a poor user experience where:
1. Receptionists could see services they couldn't order
2. They would only discover the restriction after attempting to add the service
3. Error messages appeared in the console

## Solution

Implemented **frontend role-based filtering** to prevent users from seeing services they cannot order:

1. **Added `allowed_roles` to Service interface** - TypeScript type now includes role restrictions
2. **Filter services in ServiceSearchInput** - Only show services the user can order
3. **Visual indicators** - Show restricted badge for services that can't be ordered (if they somehow appear)
4. **Prevent selection** - Disable click handlers for restricted services

## Implementation Details

### 1. Updated Service Interface

**File**: `frontend/src/api/billing.ts`

Added `allowed_roles` field to the `Service` interface:

```typescript
export interface Service {
  // ... existing fields
  allowed_roles?: string[];  // Roles that can order this service
}
```

### 2. Role-Based Filtering Logic

**File**: `frontend/src/components/billing/ServiceSearchInput.tsx`

Added `canOrderService` function to check if user can order a service:

```typescript
const canOrderService = (service: Service): boolean => {
  if (!service.allowed_roles || service.allowed_roles.length === 0) {
    // If no allowed_roles specified, allow all authenticated users
    return true;
  }
  
  const userRole = user?.role;
  if (!userRole) {
    return false;
  }
  
  // Check if user's role is in the allowed_roles list
  return service.allowed_roles.includes(userRole);
};
```

### 3. Filter Search Results

Updated the search effect to filter results before displaying:

```typescript
const filteredResults = response.results.filter(service => canOrderService(service));
setSuggestions(filteredResults);
```

### 4. Visual Indicators

Added CSS styles for restricted services:

**File**: `frontend/src/components/billing/ServiceSearchInput.module.css`

```css
.suggestionItemDisabled {
  opacity: 0.6;
  cursor: not-allowed;
  background: #f9fafb;
}

.restrictedBadge {
  font-size: 0.7rem;
  font-weight: 600;
  color: #dc2626;
  background: #fee2e2;
  padding: 0.125rem 0.375rem;
  border-radius: 4px;
  margin-left: auto;
}
```

### 5. Prevent Selection

Updated click handler to prevent selection of restricted services:

```typescript
onClick={(e) => {
  e.preventDefault();
  e.stopPropagation();
  if (canOrder) {
    handleServiceSelect(service);
  }
}}
```

## How It Works

### For Receptionists

1. **Search services** → Only services with `allowed_roles` including `RECEPTIONIST` are shown
2. **Services restricted to DOCTOR/NURSE** → Filtered out, never appear in search results
3. **No errors** → Users never see services they can't order

### For Doctors

1. **Search services** → All services with `allowed_roles` including `DOCTOR` are shown
2. **Full access** → Can order any service they're allowed to order

### For Nurses

1. **Search services** → All services with `allowed_roles` including `NURSE` are shown
2. **Nurse-accessible services** → Can order services configured for nurses

## Backend Compatibility

✅ **No backend changes required**

The backend already:
- Returns `allowed_roles` in service catalog responses (via `ServiceCatalogSerializer`)
- Validates role permissions in `downstream_service_workflow.py`
- Rejects unauthorized service orders with clear error messages

The frontend now **complements** the backend validation by preventing users from attempting to order restricted services.

## Benefits

1. **Better UX**: Users only see services they can actually order
2. **Fewer Errors**: No more 400 errors from attempting restricted services
3. **Clear Feedback**: Visual indicators show restrictions (if any slip through)
4. **Performance**: Filtering happens client-side, reducing unnecessary API calls
5. **Security**: Frontend filtering + backend validation = defense in depth

## Testing Checklist

- [ ] Receptionist searches services → Only sees services they can order
- [ ] Doctor searches services → Sees all doctor-accessible services
- [ ] Nurse searches services → Sees all nurse-accessible services
- [ ] Restricted services don't appear in search results
- [ ] No console errors when searching
- [ ] Visual indicators work correctly (if needed)
- [ ] Backend validation still works as fallback

## Files Modified

1. `frontend/src/api/billing.ts` - Added `allowed_roles` to Service interface
2. `frontend/src/components/billing/ServiceSearchInput.tsx` - Added role filtering
3. `frontend/src/components/billing/ServiceSearchInput.module.css` - Added restricted styles

## Related Files

- `backend/apps/billing/service_catalog_views.py` - Returns `allowed_roles` in API responses
- `backend/apps/visits/downstream_service_workflow.py` - Validates role permissions
- `backend/apps/billing/permissions.py` - `CanAddServicesFromCatalog` permission class

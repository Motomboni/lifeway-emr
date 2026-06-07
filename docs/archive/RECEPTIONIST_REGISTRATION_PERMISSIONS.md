# Receptionist Registration Service Permissions

## Problem

Receptionists were unable to order registration services (like "REG-001-REGISTRATI") because those services had `allowed_roles` set to `['DOCTOR', 'NURSE']` only. This prevented receptionists from handling patient registration workflows.

## Solution

Updated both backend and frontend to allow receptionists to handle **all registration services** regardless of their `allowed_roles` configuration.

## Implementation Details

### 1. Backend: ServiceCatalog Model

**File**: `backend/apps/billing/service_catalog_models.py`

Updated `can_be_ordered_by()` method to allow receptionists to order registration services:

```python
def can_be_ordered_by(self, user_role: str) -> bool:
    """
    Check if a user with the given role can order this service.
    
    Special Rules:
    - Receptionists can always order registration services 
      (service_code starts with 'REG-' or name contains 'REGISTRATION')
    - Other services follow allowed_roles strictly
    """
    # Special case: Receptionists can handle all registration services
    if user_role == 'RECEPTIONIST':
        is_registration = (
            self.service_code.upper().startswith('REG-') or
            'REGISTRATION' in self.name.upper() or
            'REGISTRATION' in (self.description or '').upper()
        )
        if is_registration:
            return True
    
    # For all other cases, check allowed_roles
    return user_role in self.allowed_roles
```

### 2. Frontend: Service Search Component

**File**: `frontend/src/components/billing/ServiceSearchInput.tsx`

Added helper function to identify registration services and updated visual indicators:

```typescript
// Check if a service is a registration service
const isRegistrationService = (service: Service): boolean => {
  const serviceCode = (service.service_code || '').toUpperCase();
  const serviceName = (service.service_name || service.name || '').toUpperCase();
  const description = (service.description || '').toUpperCase();
  
  return (
    serviceCode.startsWith('REG-') ||
    serviceName.includes('REGISTRATION') ||
    description.includes('REGISTRATION')
  );
};

// Updated isServiceOrderable to allow receptionists for registration services
const isServiceOrderable = (service: Service): boolean => {
  // ... existing checks ...
  
  // Receptionists can always order registration services (backend allows this)
  if (userRole === 'RECEPTIONIST' && isRegistrationService(service)) {
    return true;
  }
  
  return service.allowed_roles.includes(userRole);
};
```

## How Registration Services Are Identified

A service is considered a "registration service" if **any** of the following conditions are met:

1. **Service Code** starts with `REG-` (e.g., `REG-001-REGISTRATI`)
2. **Service Name** contains `REGISTRATION` (e.g., "ANC REGISTRATION", "ANTENATAL REGISTRATION")
3. **Description** contains `REGISTRATION`

The matching is **case-insensitive**.

## User Experience

### For Receptionists

1. **Search registration services** → See all registration services
2. **No warning badges** → Registration services show as fully orderable
3. **Can order successfully** → Backend allows the order
4. **Other services** → Still show warning badges if not in `allowed_roles`

### For Other Roles

- **No change** → Doctors, nurses, etc. still follow `allowed_roles` strictly
- **Registration services** → Only orderable if their role is in `allowed_roles`

## Examples of Registration Services

Based on the service catalog, registration services include:

- `REG-001-REGISTRATI` - Registration service
- `ANC REGISTRATION (1ST 3 MONTHS)` - Antenatal registration
- `ANTENATAL REGISTRATION` - General antenatal registration
- Any service with "REGISTRATION" in the name or description

## Benefits

1. **Proper Role Assignment** → Receptionists can handle registration workflows
2. **No Configuration Changes** → Existing services work without updating `allowed_roles`
3. **Backward Compatible** → Other roles unaffected
4. **Clear Logic** → Easy to identify registration services by naming convention

## Testing Checklist

- [ ] Receptionist searches "REG" → Sees registration services
- [ ] Receptionist searches "registration" → Sees registration services
- [ ] Receptionist can order registration service → Success
- [ ] Receptionist sees no warning badge on registration services
- [ ] Doctor/nurse ordering registration → Still follows `allowed_roles`
- [ ] Non-registration services → Still show restrictions for receptionists

## Files Modified

1. `backend/apps/billing/service_catalog_models.py`
   - Updated `can_be_ordered_by()` method
   - Added registration service detection logic

2. `frontend/src/components/billing/ServiceSearchInput.tsx`
   - Added `isRegistrationService()` helper function
   - Updated `isServiceOrderable()` to allow receptionists for registration services

## Related Features

This fix complements:
- **Service Catalog Role Filtering** - Receptionists see all services
- **Billing Workflow** - Receptionists can add services to bills
- **Registration Workflow** - Receptionists can now handle patient registration

## Future Enhancements

Potential improvements:
1. Add `REGISTRATION` as a workflow type in `WORKFLOW_TYPE_CHOICES`
2. Add `REGISTRATION` as a department option
3. Create dedicated registration service category
4. Add admin interface to mark services as "registration" explicitly

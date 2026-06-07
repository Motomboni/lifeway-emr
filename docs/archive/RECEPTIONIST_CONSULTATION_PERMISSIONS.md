# Receptionist Consultation Service Permissions

## Problem

Receptionists need permission to order consultation services:
- Follow Up (GOPD)
- Follow up (Consultant)
- GOPD Consultation

These are consultation services with `workflow_type = 'GOPD_CONSULT'` that were previously restricted to doctors only.

## Solution

Updated both backend and frontend to allow receptionists to order **all consultation services** (GOPD_CONSULT workflow type) regardless of their `allowed_roles` configuration.

## Implementation Details

### 1. Backend: ServiceCatalog Model

**File**: `backend/apps/billing/service_catalog_models.py`

Updated `can_be_ordered_by()` method to allow receptionists to order consultation services:

```python
def can_be_ordered_by(self, user_role: str) -> bool:
    """
    Special Rules:
    - Receptionists can always order registration services 
      (service_code starts with 'REG-' or name contains 'REGISTRATION')
    - Receptionists can always order consultation services 
      (GOPD_CONSULT workflow type, CONSULTATION department, CONS- prefix, or name patterns)
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
        
        # Receptionists can order consultation services
        # Check by workflow_type, department, service_code pattern, or name
        is_consultation = (
            self.workflow_type == 'GOPD_CONSULT' or
            self.department == 'CONSULTATION' or
            self.service_code.upper().startswith('CONS-') or
            'FOLLOW UP' in self.name.upper() or
            'FOLLOW-UP' in self.name.upper() or
            'FOLLOWUP' in self.name.upper() or
            'CONSULTATION' in self.name.upper() or
            'CONSULT' in self.name.upper()
        )
        if is_consultation:
            return True
    
    # For all other cases, check allowed_roles
    return user_role in self.allowed_roles
```

### 2. Frontend: Service Search Component

**File**: `frontend/src/components/billing/ServiceSearchInput.tsx`

Added helper function to identify consultation services and updated visual indicators:

// Check if a service is a consultation service
// Check by workflow_type, department, service_code pattern, or name
const isConsultationService = (service: Service): boolean => {
  const serviceCode = (service.service_code || '').toUpperCase();
  const serviceName = (service.service_name || service.name || '').toUpperCase();
  const department = (service.department || '').toUpperCase();
  
  return (
    service.workflow_type === 'GOPD_CONSULT' ||
    department === 'CONSULTATION' ||
    serviceCode.startsWith('CONS-') ||
    serviceName.includes('FOLLOW UP') ||
    serviceName.includes('FOLLOW-UP') ||
    serviceName.includes('FOLLOWUP') ||
    serviceName.includes('CONSULTATION') ||
    serviceName.includes('CONSULT')
  );
};

// Updated canOrderService to allow receptionists for consultation services
const canOrderService = (service: Service): boolean => {
  // ...
  if (userRole === 'RECEPTIONIST') {
    // Receptionists can order registration and consultation services
    if (isRegistrationService(service) || isConsultationService(service)) {
      return true;
    }
    // ...
  }
  // ...
};

// Updated isServiceOrderable to allow receptionists for consultation services
const isServiceOrderable = (service: Service): boolean => {
  // ...
  // Receptionists can always order registration and consultation services
  if (userRole === 'RECEPTIONIST' && (isRegistrationService(service) || isConsultationService(service))) {
    return true;
  }
  // ...
};
```

## How Consultation Services Are Identified

A service is considered a "consultation service" if **any** of the following conditions are met:

1. **Workflow Type** is `GOPD_CONSULT`
2. **Department** is `CONSULTATION`
3. **Service Code** starts with `CONS-` (e.g., `CONS-005-FOLLOWUPGO`)
4. **Service Name** contains:
   - `FOLLOW UP`
   - `FOLLOW-UP`
   - `FOLLOWUP`
   - `CONSULTATION`
   - `CONSULT`

The matching is **case-insensitive**.

This includes:
- Follow Up (GOPD)
- Follow up (Consultant)
- GOPD Consultation
- Any service with service code starting with `CONS-`
- Any service in the `CONSULTATION` department

## User Experience

### For Receptionists

1. **Search consultation services** → See all consultation services
2. **No warning badges** → Consultation services show as fully orderable
3. **Can order successfully** → Backend allows the order
4. **Creates consultation** → Consultation workflow is initiated
5. **Other services** → Still show warning badges if not in `allowed_roles`

### For Other Roles

- **No change** → Doctors, nurses, etc. still follow `allowed_roles` strictly
- **Consultation services** → Only orderable if their role is in `allowed_roles`

## Examples of Consultation Services

Based on the service catalog, consultation services include:

- **Follow Up (GOPD)** - General outpatient follow-up consultation
- **Follow up (Consultant)** - Specialist consultant follow-up
- **GOPD Consultation** - General outpatient consultation
- Any service with `workflow_type = 'GOPD_CONSULT'`

## Benefits

1. **Proper Role Assignment** → Receptionists can initiate consultation workflows
2. **No Configuration Changes** → Existing services work without updating `allowed_roles`
3. **Backward Compatible** → Other roles unaffected
4. **Clear Logic** → Consultation services identified by workflow type

## Testing Checklist

- [ ] Receptionist searches "Follow Up" → Sees consultation services
- [ ] Receptionist searches "GOPD" → Sees consultation services
- [ ] Receptionist can order consultation service → Success
- [ ] Receptionist sees no warning badge on consultation services
- [ ] Consultation workflow is initiated correctly
- [ ] Doctor/nurse ordering consultation → Still follows `allowed_roles`
- [ ] Non-consultation services → Still show restrictions for receptionists

## Files Modified

1. **`backend/apps/billing/service_catalog_models.py`**
   - Updated `can_be_ordered_by()` method
   - Added consultation service detection logic (`workflow_type == 'GOPD_CONSULT'`)

2. **`frontend/src/components/billing/ServiceSearchInput.tsx`**
   - Added `isConsultationService()` helper function
   - Updated `canOrderService()` to allow receptionists for consultation services
   - Updated `isServiceOrderable()` to allow receptionists for consultation services

## Related Features

This fix complements:
- **Receptionist Registration Permissions** - Receptionists can order registration services
- **Service Catalog Role Filtering** - Receptionists see all services
- **GOPD Consultation Workflow** - Consultation services trigger proper workflow
- **Billing Workflow** - Consultation services create billing line items

## Future Enhancements

Potential improvements:
1. Add specific consultation types (Follow Up, Initial Consultation, etc.) as separate workflow types
2. Add admin interface to mark services as "consultation" explicitly
3. Add consultation-specific permissions (e.g., receptionist can order but not access consultation)

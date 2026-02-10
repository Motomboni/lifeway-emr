# Registration Services - No Consultation Requirement Fix

## Problem

Registration services (like `REG-001-REGISTRATI`) were failing with the error:

```
Service ordering (PROCEDURE) requires a Consultation. 
Per EMR Context Document v2, all orders (Lab/Radiology/Drug/Procedure) require consultation context. 
Please ensure a consultation exists for this visit.
```

This prevented receptionists from ordering registration services, even though:
1. Receptionists have permission to handle registration services
2. Registration services are administrative/billing services, not clinical procedures
3. Registration should happen before consultation (patient registration is the first step)

## Root Cause

The backend workflow validation was enforcing consultation requirements for **all** PROCEDURE services, including registration services which are administrative/billing services that don't require clinical consultation.

## Solution

Updated the backend to allow registration services to be ordered **without consultation**:

1. **Added registration service detection** - Helper function to identify registration services
2. **Updated consultation validation** - Skip consultation requirement for registration services
3. **Made consultation nullable** - Updated `ProcedureTask` model to allow `consultation=None` for registration services
4. **Updated model validation** - Allow registration services to be created without consultation

## Implementation Details

### 1. Registration Service Detection

**File**: `backend/apps/visits/downstream_service_workflow.py`

Added helper function to identify registration services:

```python
def is_registration_service(service: ServiceCatalog) -> bool:
    """
    Check if a service is a registration service.
    
    Registration services are identified by:
    - Service code starting with 'REG-'
    - Service name containing 'REGISTRATION'
    - Description containing 'REGISTRATION'
    """
    service_code = (service.service_code or '').upper()
    service_name = (service.name or '').upper()
    description = (service.description or '').upper()
    
    return (
        service_code.startswith('REG-') or
        'REGISTRATION' in service_name or
        'REGISTRATION' in description
    )
```

### 2. Updated Consultation Validation

**File**: `backend/apps/visits/downstream_service_workflow.py`

Updated the main workflow function to skip consultation validation for registration services:

```python
# Exception: Registration services don't require consultation
if service.requires_consultation and not is_registration_service(service):
    validate_visit_consultation_chain(...)
```

### 3. Updated Procedure Service Handler

**File**: `backend/apps/visits/downstream_service_workflow.py`

Updated `_order_procedure_service()` to:
- Allow registration services without consultation requirement
- Set `consultation=None` for registration services
- Create `ProcedureTask` with `consultation=None` for registration services

### 4. Made Consultation Nullable

**File**: `backend/apps/clinical/procedure_models.py`

Updated `ProcedureTask` model:

```python
consultation = models.ForeignKey(
    'consultations.Consultation',
    on_delete=models.PROTECT,
    null=True,  # ← Now nullable
    blank=True,  # ← Can be blank
    related_name='procedure_tasks',
    help_text="Consultation this procedure belongs to. Required for clinical procedures, optional for registration/administrative services."
)
```

### 5. Updated Model Validation

**File**: `backend/apps/clinical/procedure_models.py`

Updated `clean()` method to:
- Allow `consultation=None` for registration services
- Still require consultation for non-registration procedures
- Validate consultation belongs to visit (if provided)

## Database Migration

Created migration: `0003_make_procedure_consultation_nullable.py`

This migration:
- Makes `consultation` field nullable in `ProcedureTask` table
- Allows existing procedure tasks to keep their consultations
- Enables registration services to be created without consultation

**To apply migration:**
```bash
python manage.py migrate clinical
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
2. **Order registration service** → No consultation required
3. **Service added to bill** → Creates `ProcedureTask` with `consultation=None`
4. **Billing line item created** → Service appears in billing

### For Other Roles

- **No change** → Clinical procedures still require consultation
- **Registration services** → Can also be ordered without consultation (if in `allowed_roles`)

## Examples of Registration Services

- `REG-001-REGISTRATI` - General registration
- `ANC REGISTRATION (1ST 3 MONTHS)` - Antenatal registration
- `ANTENATAL REGISTRATION` - General antenatal registration
- Any service with "REGISTRATION" in name/description

## Benefits

1. **Proper Workflow** → Registration happens before consultation (as it should)
2. **Receptionist Access** → Receptionists can handle all registration services
3. **No Breaking Changes** → Clinical procedures still require consultation
4. **Flexible Design** → Registration services identified by naming convention

## Testing Checklist

- [ ] Receptionist orders `REG-001-REGISTRATI` → Success (no consultation required)
- [ ] Receptionist orders "ANC REGISTRATION" → Success (no consultation required)
- [ ] Doctor orders clinical procedure → Still requires consultation
- [ ] ProcedureTask created with `consultation=None` for registration services
- [ ] Billing line item created correctly
- [ ] Migration applied successfully

## Files Modified

1. **`backend/apps/visits/downstream_service_workflow.py`**
   - Added `is_registration_service()` helper function
   - Updated consultation validation to skip registration services
   - Updated `_order_procedure_service()` to handle registration services
   - Set `consultation=None` for registration services before routing

2. **`backend/apps/clinical/procedure_models.py`**
   - Made `consultation` field nullable (`null=True, blank=True`)
   - Updated `clean()` method to allow `consultation=None` for registration services
   - Updated validation logic to check for registration services

3. **`backend/apps/clinical/migrations/0003_make_procedure_consultation_nullable.py`** (NEW)
   - Migration to make `consultation` nullable in database

## Related Features

This fix complements:
- **Receptionist Registration Permissions** - Receptionists can order registration services
- **Service Catalog Role Filtering** - Registration services visible to receptionists
- **Billing Workflow** - Registration services create billing line items

## Future Enhancements

Potential improvements:
1. Add `REGISTRATION` as a workflow type in `WORKFLOW_TYPE_CHOICES`
2. Add `REGISTRATION` as a department option
3. Create dedicated registration service category
4. Add admin interface to mark services as "registration" explicitly

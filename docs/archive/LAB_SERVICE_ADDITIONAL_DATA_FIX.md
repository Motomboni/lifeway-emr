# Lab Service Additional Data Fix

## Problem
When doctors tried to order LAB services from the Service Catalog, the system was returning a 400 Bad Request error:
```
Error: ["LAB service requires 'tests_requested' in additional_data."]
```

## Root Cause
The backend requires `tests_requested` (as an array) in the `additional_data` field when ordering LAB services, but the frontend was not collecting this information before submitting the order.

## Solution

### 1. Created `LabOrderDetailsForm` Component
**File:** `frontend/src/components/laboratory/LabOrderDetailsForm.tsx`

A modal form similar to `PrescriptionDetailsForm` that collects:
- **Tests Requested** (required): List of tests to be performed
  - Can be entered as comma-separated or one per line
  - Pre-filled with the service name
  - Converted to array before submission
- **Clinical Indication** (optional): Reason for ordering the tests

### 2. Updated `ServiceCatalogInline` Component
**File:** `frontend/src/components/inline/ServiceCatalogInline.tsx`

**Changes:**
1. Added import for `LabOrderDetailsForm`
2. Added state for `showLabOrderForm`
3. Updated `handleServiceSelect()` to detect LAB services and show the form:
   ```typescript
   if (service.department === 'LAB') {
     setSelectedService(service);
     setShowServiceSearch(false);
     setShowLabOrderForm(true);
     return;
   }
   ```
4. Added `handleLabOrderSubmit()` to process lab order form submission
5. Added `handleLabOrderCancel()` to handle form cancellation
6. Updated UI conditions to include lab order form modal

## How It Works Now

### Before (❌ Error):
```
Doctor selects LAB service → 
System tries to order directly → 
Backend rejects (missing tests_requested) → 
Error displayed
```

### After (✅ Fixed):
```
Doctor selects LAB service → 
Lab Order Details Form appears → 
Doctor enters tests and clinical indication → 
Form submits with additional_data → 
Backend accepts and creates LabOrder → 
Success!
```

## Service-Specific Forms

The system now has specialized forms for different service types:

| Service Type | Form Component | Required Fields |
|--------------|----------------|-----------------|
| **PHARMACY** | `PrescriptionDetailsForm` | dosage, frequency, duration, instructions |
| **LAB** | `LabOrderDetailsForm` | tests_requested |
| **RADIOLOGY** | *(Direct order)* | None (may need form in future) |
| **PROCEDURE** | *(Direct order)* | None |

## Backend Requirements

From `backend/apps/visits/downstream_service_workflow.py`:

```python
def _order_lab_service(...):
    # Extract additional data
    tests_requested = additional_data.get('tests_requested', [])
    clinical_indication = additional_data.get('clinical_indication', '')
    
    if not tests_requested:
        raise ValidationError("LAB service requires 'tests_requested' in additional_data.")
```

**Format:**
```json
{
  "additional_data": {
    "tests_requested": ["Complete Blood Count", "Malaria Parasite"],
    "clinical_indication": "Suspected malaria with fever"
  }
}
```

## Testing
Try ordering a LAB service:
1. Open a patient visit
2. Click "Search & Order Service"
3. Search for a LAB service (e.g., "Complete Blood Count")
4. Select it
5. Fill in the Lab Order Details form
6. Submit
7. Should see success message: "Lab order for [service name] created successfully"

## Files Modified
1. ✅ `frontend/src/components/laboratory/LabOrderDetailsForm.tsx` (NEW)
2. ✅ `frontend/src/components/inline/ServiceCatalogInline.tsx` (MODIFIED)

## Related Documentation
- `SERVICE_CATALOG_WORKFLOW_GUIDE.md` - Overall workflow documentation
- `backend/apps/visits/DOWNSTREAM_SERVICE_WORKFLOW.md` - Backend service ordering logic


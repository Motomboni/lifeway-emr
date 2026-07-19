# Radiology Service Additional Data Implementation

## Problem
When trying to order RADIOLOGY services from the Service Catalog:
1. **Backend**: The `_order_radiology_service` function was **referenced but not implemented** - would cause a `NameError` if anyone tried to order a radiology service
2. **Frontend**: No form to collect radiology-specific details like study type, clinical indication, and instructions

## Solution

### 1. Implemented Missing Backend Function
**File:** `backend/apps/visits/downstream_service_workflow.py`

Created the `_order_radiology_service()` function that:
- Validates the service is a RADIOLOGY_STUDY workflow type
- Validates service requirements (visit, consultation)
- Validates only DOCTOR role can order radiology services
- Extracts additional_data fields:
  - `study_type`: Type of imaging study (defaults to service name if not provided)
  - `study_code`: Study code (defaults to service_code if not provided)
  - `clinical_indication`: Reason for ordering the study (optional)
  - `instructions`: Special instructions for radiographer (optional)
- Creates RadiologyRequest object
- Auto-generates billing
- Returns tuple of (RadiologyRequest, BillingLineItem)

**Backend Format:**
```python
def _order_radiology_service(
    service: ServiceCatalog,
    visit: Visit,
    consultation: Consultation,
    user: Optional[User],
    additional_data: Optional[Dict[str, Any]],
) -> Tuple[RadiologyRequest, Any]:
    # Extract data
    study_type = additional_data.get('study_type', service.name)
    clinical_indication = additional_data.get('clinical_indication', '')
    instructions = additional_data.get('instructions', '')
    
    # Create RadiologyRequest
    radiology_request = RadiologyRequest.objects.create(
        visit=visit,
        consultation=consultation,
        ordered_by=user,
        study_type=study_type,
        study_code=study_code,
        clinical_indication=clinical_indication,
        instructions=instructions,
        status='PENDING',
    )
    
    # Auto-generate billing
    billing_line_item = create_billing_line_item_from_service(...)
    
    return radiology_request, billing_line_item
```

### 2. Created `RadiologyOrderDetailsForm` Component
**File:** `frontend/src/components/radiology/RadiologyOrderDetailsForm.tsx`

A modal form that collects:
- **Study Type** (required): Type of imaging study
  - Pre-filled with the service name
  - Can be customized by doctor
- **Clinical Indication** (optional): Reason for ordering the study
- **Special Instructions** (optional): Instructions for the radiographer

**UI Features:**
- Reuses the same CSS styling as PrescriptionDetailsForm and LabOrderDetailsForm
- Clean, professional medical form design
- Validation on required fields
- Loading state during submission
- Cancel/Submit actions

### 3. Updated `ServiceCatalogInline` Component
**File:** `frontend/src/components/inline/ServiceCatalogInline.tsx`

**Changes:**
1. Added import for `RadiologyOrderDetailsForm`
2. Added state for `showRadiologyOrderForm`
3. Updated `handleServiceSelect()` to detect RADIOLOGY services:
   ```typescript
   if (service.department === 'RADIOLOGY') {
     setSelectedService(service);
     setShowServiceSearch(false);
     setShowRadiologyOrderForm(true);
     return;
   }
   ```
4. Added `handleRadiologyOrderSubmit()` to process radiology order form submission
5. Added `handleRadiologyOrderCancel()` to handle form cancellation
6. Updated UI conditions to include radiology order form modal

## How It Works Now

### Workflow:
```
Doctor selects RADIOLOGY service → 
Radiology Order Details Form appears → 
Doctor enters study type, clinical indication, and instructions → 
Form submits with additional_data → 
Backend creates RadiologyRequest & generates billing → 
Success!
```

## Service-Specific Forms Summary

The system now has specialized forms for all major service types:

| Service Type | Form Component | Required Fields |
|--------------|----------------|-----------------|
| **PHARMACY** | `PrescriptionDetailsForm` | dosage, frequency, duration, instructions |
| **LAB** | `LabOrderDetailsForm` | tests_requested |
| **RADIOLOGY** | `RadiologyOrderDetailsForm` | study_type |
| **PROCEDURE** | *(Direct order)* | None |

## API Format

When ordering a radiology service, the frontend sends:

```json
{
  "visit_id": 235,
  "department": "RADIOLOGY",
  "service_code": "RAD-XRAY-CHEST",
  "additional_data": {
    "study_type": "Chest X-Ray PA",
    "clinical_indication": "Suspected pneumonia",
    "instructions": "Focus on right lower lobe"
  }
}
```

The backend creates:
1. **RadiologyRequest** object with:
   - visit (ForeignKey)
   - consultation (ForeignKey)
   - ordered_by (User)
   - study_type
   - study_code
   - clinical_indication
   - instructions
   - status = 'PENDING'

2. **BillingLineItem** for the service

## Testing

To test radiology ordering:

1. **Create a radiology service in ServiceCatalog:**
   ```python
   from apps.billing.service_catalog_models import ServiceCatalog
   
   ServiceCatalog.objects.create(
       department='RADIOLOGY',
       service_code='RAD-XRAY-CHEST',
       name='Chest X-Ray PA',
       amount=7500.00,
       category='RADIOLOGY',
       workflow_type='RADIOLOGY_STUDY',
       requires_visit=True,
       requires_consultation=True,
       auto_bill=True,
       bill_timing='BEFORE',
       allowed_roles=['DOCTOR'],
       is_active=True,
   )
   ```

2. **Test ordering:**
   - Open a patient visit
   - Click "Search & Order Service"
   - Search for "Chest X-Ray"
   - Select it
   - Fill in the Radiology Order Details form
   - Submit
   - Should see: "Radiology order for Chest X-Ray PA created successfully"

3. **Verify in database:**
   ```python
   from apps.radiology.models import RadiologyRequest
   
   # Check created request
   rad_request = RadiologyRequest.objects.latest('id')
   print(f"Study Type: {rad_request.study_type}")
   print(f"Status: {rad_request.status}")
   print(f"Clinical Indication: {rad_request.clinical_indication}")
   ```

## Benefits

### ✅ Complete Implementation
- Backend function implemented (was missing)
- Frontend form created
- Full integration with Service Catalog workflow

### ✅ Consistent Pattern
- Follows the same pattern as LAB and PHARMACY services
- Reuses existing CSS for consistent UI
- Same submission flow and error handling

### ✅ Medical Best Practices
- Collects clinical indication for imaging studies
- Allows special instructions for radiographers
- Proper documentation trail

### ✅ Billing Integration
- Automatically creates billing line items
- Supports "BEFORE" payment (pay first, then study)
- Integrates with receptionist dashboard

## Files Modified/Created

1. ✅ `backend/apps/visits/downstream_service_workflow.py` (MODIFIED - added missing function)
2. ✅ `frontend/src/components/radiology/RadiologyOrderDetailsForm.tsx` (NEW)
3. ✅ `frontend/src/components/inline/ServiceCatalogInline.tsx` (MODIFIED)

## Related Documentation
- `SERVICE_CATALOG_WORKFLOW_GUIDE.md` - Overall workflow documentation
- `LAB_SERVICE_ADDITIONAL_DATA_FIX.md` - LAB service implementation (similar pattern)
- `backend/apps/visits/DOWNSTREAM_SERVICE_WORKFLOW.md` - Backend service ordering logic

## Summary

**Before:** 
- ❌ Backend function missing (would crash)
- ❌ No frontend form

**After:**
- ✅ Backend function implemented
- ✅ Frontend form created
- ✅ Full integration working
- ✅ Consistent with LAB and PHARMACY patterns

All three major clinical services (PHARMACY, LAB, RADIOLOGY) now have complete form-based ordering workflows! 🎉


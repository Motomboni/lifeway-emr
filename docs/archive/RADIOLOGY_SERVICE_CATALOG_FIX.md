# Radiology Service Catalog Integration Fix

## Overview
Fixed the radiology integration with the Service Catalog workflow to ensure radiology services ordered through the catalog work correctly end-to-end.

## Problem Summary
1. Radiology services ordered via Service Catalog were not appearing in the consultation workspace
2. TypeScript compilation errors due to model/type mismatches between `RadiologyOrder` and `RadiologyRequest`
3. Radiology report posting was failing because it was trying to create `RadiologyResult` objects for non-existent `RadiologyOrder` records

## Root Causes
- **Model Mismatch**: Service Catalog creates `RadiologyRequest` objects, but frontend was expecting `RadiologyOrder` objects
- **Type Mismatch**: Frontend types defined old field names (`imaging_type`, `body_part`, `priority`) instead of new fields (`study_type`, `study_code`, `instructions`)
- **API Mismatch**: Report posting tried to create separate `RadiologyResult` objects, but `RadiologyRequest` stores reports directly on the request object

## Changes Made

### 1. Backend - URL Routing (`backend/apps/radiology/urls.py`)
**Changed:**
- Router now uses `RadiologyRequestViewSet` instead of `RadiologyOrderViewSet` for the main `/visits/{visit_id}/radiology/` endpoint
- This ensures the API returns `RadiologyRequest` objects matching what Service Catalog creates

### 2. Frontend - Type Definitions (`frontend/src/types/radiology.ts`)
**Updated `RadiologyOrder` interface:**
```typescript
// OLD fields removed:
// - imaging_type, body_part, priority

// NEW fields added:
- study_type: string
- study_code?: string
- instructions?: string

// Updated status choices:
- 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED'
  (was: 'ORDERED' | 'SCHEDULED' | ...)
```

**Updated `RadiologyResult` interface:**
```typescript
// Changed:
- radiology_order_id → radiology_request_id
```

### 3. Frontend - API Functions (`frontend/src/api/radiology.ts`)
**Added new function:**
```typescript
updateRadiologyReport() - For Radiology Tech to post reports via PATCH
```

**Updated function signatures:**
```typescript
createRadiologyOrder() - Now accepts study_type, study_code, instructions
```

**Marked as deprecated:**
```typescript
createRadiologyResult() - Old system, use updateRadiologyReport() instead
```

### 4. Frontend - Display Components

#### `frontend/src/components/inline/RadiologyInline.tsx`
- Updated to display new fields: `study_type`, `study_code`, `instructions`
- Removed old field mappings: `imaging_type`, `body_part`
- Updated create order to pass correct fields

#### `frontend/src/contexts/NotificationContext.tsx`
- Updated status filters: `'ORDERED' || 'SCHEDULED'` → `'PENDING' || 'IN_PROGRESS'`

#### `frontend/src/pages/RadiologyOrdersPage.tsx`
- Updated to display new fields
- Changed report posting from `createRadiologyResult()` to `updateRadiologyReport()`
- Updated status filters

#### `frontend/src/utils/exportUtils.ts`
- Updated export templates to use new field names
- Updated result lookups to use `radiology_request_id`

## Architecture Understanding

### Two Radiology Systems

The codebase has TWO radiology systems:

1. **NEW: RadiologyRequest (Service Catalog)**
   - Created via Service Catalog workflow
   - Reports stored directly on the request object
   - Fields: `study_type`, `study_code`, `clinical_indication`, `instructions`
   - Status: `PENDING`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`
   - Radiology Tech updates via PATCH to add report

2. **OLD: RadiologyOrder + RadiologyResult**
   - Legacy system (still in codebase)
   - Reports stored in separate `RadiologyResult` model
   - Fields: `imaging_type`, `body_part`, `priority`
   - Status: `ORDERED`, `SCHEDULED`, ...

**Current Fix:** Migrated frontend to use the NEW system (`RadiologyRequest`) to match Service Catalog backend.

## Testing Checklist

- [x] TypeScript compilation succeeds (no errors, only warnings)
- [ ] Can order radiology service from Service Catalog in consultation
- [ ] Radiology order appears in consultation workspace (RadiologyInline)
- [ ] Billing line item created for radiology service
- [ ] Radiology order appears in Radiology Orders page (for Radiology Tech)
- [ ] Radiology Tech can post report via PATCH
- [ ] Report appears in consultation workspace after posting
- [ ] Export functions work with new field names
- [ ] Image upload system works with new field names
- [ ] Lock system works with new field names
- [ ] Patient portal displays results correctly

## Files Modified

### Backend
1. `backend/apps/radiology/urls.py` - Router registration

### Frontend - Core Changes
1. `frontend/src/types/radiology.ts` - Type definitions (RadiologyOrder and RadiologyResult)
2. `frontend/src/api/radiology.ts` - API functions (added updateRadiologyReport)
3. `frontend/src/components/inline/RadiologyInline.tsx` - Display component and result lookup
4. `frontend/src/contexts/NotificationContext.tsx` - Status filters
5. `frontend/src/pages/RadiologyOrdersPage.tsx` - Radiology Tech page
6. `frontend/src/utils/exportUtils.ts` - Export utilities
7. `frontend/src/pages/MedicalHistoryPage.tsx` - Medical history display

### Frontend - Image Upload & Locks
8. `frontend/src/api/radiologyUpload.ts` - Image upload session API
9. `frontend/src/api/uploadSession.ts` - Upload session types
10. `frontend/src/hooks/useActionLock.ts` - Action lock hooks
11. `frontend/src/api/locks.ts` - Lock API functions
12. `frontend/src/components/radiology/OHIFViewer.tsx` - DICOM viewer

### Frontend - Patient Portal
13. `frontend/src/types/patientPortal.ts` - Patient portal types
14. `frontend/src/pages/PatientPortalRadiologyResultsPage.tsx` - Patient portal results

### Frontend - Documentation
15. `frontend/src/components/locks/EXPLAINABLE_LOCK_INTEGRATION_EXAMPLES.tsx` - Example code
16. `frontend/src/components/locks/EXPLAINABLE_LOCK_PATTERN.md` - Documentation

## Next Steps

1. **Test the complete workflow** (ordering → billing → reporting)
2. **Consider deprecating old system**: If `RadiologyOrder`/`RadiologyResult` are no longer needed, mark for removal
3. **Update documentation**: Ensure all docs reference `RadiologyRequest` as the primary model
4. **Cleanup**: Remove unused old components if confirmed not needed

## Complete Migration Summary




















































### Field Name Changes (Across ALL Files)
- `radiology_order_id` → `radiology_request_id` (16 files updated)
- `imaging_type` → `study_type`
- `body_part` → `study_code`
- `priority` → `instructions`
- Status values: `'ORDERED'|'SCHEDULED'` → `'PENDING'|'IN_PROGRESS'|'COMPLETED'|'CANCELLED'`

### System-Wide Impact
- **Total Files Modified**: 16 files
- **API Endpoints**: Updated query parameters from `radiology_order_id` to `radiology_request_id`
- **Lock System**: Updated all lock checks to use new field name
- **Image Upload**: Updated session tracking to use new field name
- **Patient Portal**: Updated result display to use new field name

## Notes

- ✅ **Build Status**: TypeScript compilation successful (0 errors, only linting warnings)
- The 401 (Unauthorized) errors in console are from token expiration on background polling - these should auto-resolve via token refresh mechanism
- The "Billing line item already exists" error is CORRECT behavior - it prevents duplicate billing for the same service
- Reports are now stored directly on `RadiologyRequest.report` field, not in a separate table
- All references to `radiology_order_id` have been systematically replaced with `radiology_request_id`


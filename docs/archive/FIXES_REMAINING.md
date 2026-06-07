# Remaining Compilation Fixes

## Issues to Fix

### 1. React Icons Type Errors
**Problem:** React Icons components showing as invalid JSX components. This is a TypeScript/React version compatibility issue.

**Solution:** Update React and TypeScript types, or use type assertions.

### 2. Missing RadiologyTestTemplate Type
**File:** `frontend/src/components/inline/RadiologyInline.tsx:60`
**Fix:** Change `RadiologyTestTemplate[]` to `any[]`

### 3. Missing checkRadiologyViewLock Function
**File:** `frontend/src/hooks/useActionLock.ts:74`
**Fix:** Import from `../api/locks` or add the function

### 4. Function Signature Mismatches
**Files:** 
- `frontend/src/hooks/useRadiologyOrders.ts` - `createRadiologyOrder` and `createRadiologyResult` expect different signatures
- `frontend/src/pages/RadiologyOrdersPage.tsx` - Same issue

**Fix:** Update function calls to match API signatures

### 5. Missing FaWifiSlash Icon
**File:** `frontend/src/pages/RadiologyUploadStatusPage.tsx:27`
**Fix:** Remove or replace with `FaWifi` with conditional rendering


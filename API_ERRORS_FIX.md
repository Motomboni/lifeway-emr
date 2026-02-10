# API Errors Fix Summary

## Issues Fixed

### 1. Revenue Leak Detection - 404 Errors ✅
**Problem:** Frontend was calling `/billing/revenue-leak/` but backend uses `/billing/leaks/`

**Solution:** Updated all revenue leak API endpoints in `frontend/src/api/revenueLeaks.ts`:
- `/billing/revenue-leak/` → `/billing/leaks/`
- `/billing/revenue-leak/{id}/` → `/billing/leaks/{id}/`
- `/billing/revenue-leak/daily_aggregation/` → `/billing/leaks/daily_aggregation/`
- `/billing/revenue-leak/summary/` → `/billing/leaks/summary/`
- `/billing/revenue-leak/{id}/resolve/` → `/billing/leaks/{id}/resolve/`
- `/billing/revenue-leak/detect_all/` → `/billing/leaks/detect_all/`

### 2. Patient Registration - 403 Forbidden ✅
**Problem:** Admin users couldn't register patients due to backend permission checks

**Solution:** Updated `backend/apps/patients/permissions.py`:
- `CanRegisterPatient`: Now allows `['RECEPTIONIST', 'ADMIN']`
- `CanManagePatients`: Now allows `['RECEPTIONIST', 'ADMIN']`
- `CanSearchPatient`: Now allows `['RECEPTIONIST', 'ADMIN', 'DOCTOR', 'LAB_TECH', 'RADIOLOGY_TECH', 'PHARMACIST']`

### 3. Radiology Upload Sessions - 500 Errors ✅
**Problem:** Frontend was calling `/visits/0/radiology/upload-sessions/` with invalid visit ID 0

**Solution:** Updated `frontend/src/api/radiologyUpload.ts`:
- `/visits/0/radiology/upload-sessions/pending/` → `/radiology/upload-sessions/pending/`
- `/visits/0/radiology/upload-sessions/failed/` → `/radiology/upload-sessions/failed/`
- `/visits/0/radiology/upload-sessions/{id}/retry/` → `/radiology/upload-sessions/{id}/retry/`
- `/visits/0/radiology/upload-sessions/{id}/` → `/radiology/upload-sessions/{id}/`
- `/visits/0/radiology/{id}/` → `/radiology/orders/{id}/`

### 4. Reconciliation Today - 500 Error ⚠️
**Status:** Endpoint exists in backend. The 500 error may be due to:
- Missing data in database
- Service method error
- Need to check backend logs for specific error

**Action Required:** Check backend logs when accessing reconciliation page to identify the specific error.

## Files Modified

1. `frontend/src/api/revenueLeaks.ts` - Fixed all endpoint URLs
2. `backend/apps/patients/permissions.py` - Added ADMIN to all patient permissions
3. `frontend/src/api/radiologyUpload.ts` - Fixed upload session endpoints

## Testing

### Revenue Leak Detection
1. Login as Admin
2. Navigate to `/billing/revenue-leaks`
3. Should load without 404 errors

### Patient Registration
1. Login as Admin
2. Navigate to `/patients/register`
3. Fill in form and submit
4. Should create patient successfully (no 403 error)

### Radiology Upload Status
1. Login as Admin or Radiology Tech
2. Navigate to `/radiology/upload-status`
3. Should load without 500 errors (if there are upload sessions)

### Reconciliation
1. Login as Admin or Receptionist
2. Navigate to `/reconciliation`
3. Check backend logs if 500 error persists

## Next Steps

1. ✅ Test revenue leak detection page
2. ✅ Test patient registration as Admin
3. ✅ Test radiology upload status page
4. ⚠️ Investigate reconciliation 500 error (check backend logs)

## Status

✅ **Revenue Leak URLs Fixed**
✅ **Patient Permissions Fixed**
✅ **Radiology Upload URLs Fixed**
⚠️ **Reconciliation 500 Error** - Needs backend log investigation


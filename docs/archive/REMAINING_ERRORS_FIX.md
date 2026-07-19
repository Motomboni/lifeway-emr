# Remaining API Errors Fix

## Issues Identified

### 1. ✅ Timeline Endpoint - 500 Error
**Problem:** Timeline view was using `visit_pk` but URL uses `visit_id`, causing a mismatch.

**Solution:** Updated `backend/apps/visits/timeline_views.py`:
- Changed `visit_pk` to `visit_id` in `get_queryset()`, `list()`, and `retrieve()` methods
- Added `.order_by('timestamp')` to ensure chronological ordering

**Files Modified:**
- `backend/apps/visits/timeline_views.py`

### 2. ⚠️ Lock Endpoint - 404 Error
**Problem:** `/locks/consultation/` endpoint returns 404.

**Status:** The backend has a `consultation` action in `LockEvaluationViewSet`. The endpoint should be `/locks/consultation/` which matches the frontend call. This might be a routing issue or the server needs to be restarted.

**Action Required:** 
- Verify the lock URLs are properly included in `backend/core/urls.py`
- Restart the Django server to ensure URL changes are loaded

### 3. ⚠️ Revenue Leak Endpoints - 404 Error (Cached)
**Problem:** Frontend is still calling `/billing/revenue-leak/` instead of `/billing/leaks/`.

**Status:** The file has been updated correctly, but the browser might be using cached JavaScript.

**Action Required:**
- Hard refresh the browser (Ctrl+Shift+R or Ctrl+F5)
- Clear browser cache
- Restart the frontend dev server

### 4. ⚠️ Patient Registration - 403 Error
**Problem:** Admin users still getting 403 when registering patients.

**Status:** Backend permissions have been updated, but the server needs to be restarted.

**Action Required:**
- Restart the Django backend server
- Verify the user's role is actually 'ADMIN' in the database

### 5. ⚠️ Radiology Upload Sessions - Still Using Old Endpoints
**Problem:** Errors show `/visits/0/radiology/upload-sessions/` is still being called.

**Status:** The API file has been updated, but the page might be using cached code or there's another component calling the old endpoints.

**Action Required:**
- Hard refresh the browser
- Check if `RadiologyUploadStatusPage.tsx` is using the updated API functions
- Restart frontend dev server

## Files Modified

1. ✅ `backend/apps/visits/timeline_views.py` - Fixed `visit_pk` → `visit_id`

## Testing Checklist

### Timeline Endpoint
- [ ] Navigate to a visit details page
- [ ] Check browser console for timeline errors
- [ ] Timeline should load without 500 errors

### Lock Endpoint
- [ ] Check if `/locks/consultation/` endpoint exists
- [ ] Restart Django server
- [ ] Test lock checking functionality

### Revenue Leak
- [ ] Hard refresh browser (Ctrl+Shift+R)
- [ ] Navigate to `/billing/revenue-leaks`
- [ ] Should load without 404 errors

### Patient Registration
- [ ] Restart Django server
- [ ] Login as Admin
- [ ] Try registering a patient
- [ ] Should work without 403 error

### Radiology Upload Status
- [ ] Hard refresh browser
- [ ] Navigate to `/radiology/upload-status`
- [ ] Should use new endpoints without `/visits/0/`

## Next Steps

1. ✅ Fix timeline endpoint parameter mismatch
2. ⚠️ Restart Django backend server
3. ⚠️ Hard refresh browser / restart frontend dev server
4. ⚠️ Verify lock endpoint routing
5. ⚠️ Test all fixed endpoints

## Status

✅ **Timeline Endpoint Fixed**
⚠️ **Lock Endpoint** - Needs server restart / routing verification
⚠️ **Revenue Leak** - Needs browser cache clear
⚠️ **Patient Registration** - Needs server restart
⚠️ **Radiology Upload** - Needs browser cache clear


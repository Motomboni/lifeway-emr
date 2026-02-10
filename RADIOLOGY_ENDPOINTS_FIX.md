# Radiology Endpoints Fix

## Issue
Frontend was calling `/radiology/orders/?visit=${visitId}` and `/radiology/results/?visit=${visitId}`, but radiology orders are visit-scoped and should be under `/visits/{visit_id}/radiology/`.

## Changes Made

### 1. ✅ Fixed `fetchRadiologyOrders`
**File:** `frontend/src/api/radiology.ts`
- **Before:** `/radiology/orders/?visit=${visitId}`
- **After:** `/visits/${visitId}/radiology/`

### 2. ✅ Fixed `createRadiologyOrder`
**File:** `frontend/src/api/radiology.ts`
- **Before:** `/radiology/orders/` with `visit` in body
- **After:** `/visits/${visitId}/radiology/` with `visitId` as first parameter

### 3. ✅ Fixed `fetchRadiologyResults`
**File:** `frontend/src/api/radiology.ts`
- **Before:** `/radiology/results/?visit=${visitId}`
- **After:** `/visits/${visitId}/radiology/results/`

### 4. ✅ Fixed `createRadiologyResult`
**File:** `frontend/src/api/radiology.ts`
- **Before:** `/radiology/results/` with data in body
- **After:** `/visits/${visitId}/radiology/results/` with `visitId` as first parameter

### 5. ✅ Fixed `getRadiologyOrder`
**Files:** 
- `frontend/src/api/radiologyOrders.ts`
- `frontend/src/api/radiologyUpload.ts`
- **Before:** `/radiology/orders/${orderId}/`
- **After:** `/visits/${visitId}/radiology/${orderId}/` with `visitId` as first parameter

### 6. ✅ Updated Hook Calls
**File:** `frontend/src/hooks/useRadiologyOrders.ts`
- Updated `createRadiologyOrder` to pass `visitId` as first parameter
- Updated `createRadiologyResult` to pass `visitId` as first parameter

## Files Modified

1. `frontend/src/api/radiology.ts` - Fixed all radiology order/result endpoints
2. `frontend/src/api/radiologyOrders.ts` - Fixed `getRadiologyOrder` signature
3. `frontend/src/api/radiologyUpload.ts` - Fixed `getRadiologyOrder` signature
4. `frontend/src/hooks/useRadiologyOrders.ts` - Updated function calls

## Breaking Changes

⚠️ **Note:** The following functions now require `visitId` as the first parameter:
- `createRadiologyOrder(visitId, data)` - Previously `createRadiologyOrder(data)` with `visit` in data
- `createRadiologyResult(visitId, data)` - Previously `createRadiologyResult(data)`
- `getRadiologyOrder(visitId, orderId)` - Previously `getRadiologyOrder(orderId)`

## Components That Need Updates

The following components may need updates to pass `visitId`:
- `frontend/src/components/radiology/RadiologyOrderDetails.tsx` - Uses `getRadiologyOrder`
- `frontend/src/pages/RadiologyOrdersPage.tsx` - Uses `createRadiologyResult`

## Testing

1. Navigate to a visit with radiology orders
2. Check browser console - should not see 404 errors for `/radiology/orders/`
3. Try creating a radiology order - should work
4. Try creating a radiology result - should work
5. Try viewing radiology order details - should work

## Status

✅ **All radiology endpoints updated to use visit-scoped URLs**


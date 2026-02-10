# Radiology Endpoints Fix - Complete

## Summary
Fixed all radiology endpoints to use visit-scoped URLs (`/visits/{visit_id}/radiology/`) instead of global URLs (`/radiology/orders/`).

## All Changes Made

### API Functions Updated

1. **`fetchRadiologyOrders(visitId)`**
   - ✅ Changed from `/radiology/orders/?visit=${visitId}` to `/visits/${visitId}/radiology/`

2. **`createRadiologyOrder(visitId, data)`**
   - ✅ Changed signature to require `visitId` as first parameter
   - ✅ Changed from `/radiology/orders/` to `/visits/${visitId}/radiology/`

3. **`fetchRadiologyResults(visitId)`**
   - ✅ Changed from `/radiology/results/?visit=${visitId}` to `/visits/${visitId}/radiology/results/`

4. **`createRadiologyResult(visitId, data)`**
   - ✅ Changed signature to require `visitId` as first parameter
   - ✅ Changed from `/radiology/results/` to `/visits/${visitId}/radiology/results/`

5. **`getRadiologyOrder(visitId, orderId)`**
   - ✅ Changed signature to require `visitId` as first parameter
   - ✅ Changed from `/radiology/orders/${orderId}/` to `/visits/${visitId}/radiology/${orderId}/`

### Components Updated

1. **`RadiologyOrderDetails`**
   - ✅ Added `visitId` prop
   - ✅ Updated to pass `visitId` to `getRadiologyOrder`

2. **`RadiologyOrdersPage`**
   - ✅ Updated `createRadiologyResult` call to pass `visitId`
   - ✅ Updated `RadiologyOrderDetails` usage to pass `visitId`

3. **`useRadiologyOrders` hook**
   - ✅ Updated `createRadiologyOrder` to pass `visitId` as first parameter
   - ✅ Updated `createRadiologyResult` to pass `visitId` as first parameter

## Files Modified

1. `frontend/src/api/radiology.ts` - All radiology order/result endpoints
2. `frontend/src/api/radiologyOrders.ts` - `getRadiologyOrder` signature
3. `frontend/src/api/radiologyUpload.ts` - `getRadiologyOrder` signature
4. `frontend/src/hooks/useRadiologyOrders.ts` - Function calls updated
5. `frontend/src/components/radiology/RadiologyOrderDetails.tsx` - Added `visitId` prop
6. `frontend/src/pages/RadiologyOrdersPage.tsx` - Updated function calls

## Testing Checklist

- [ ] Navigate to a visit with radiology orders
- [ ] Check browser console - should not see 404 errors for `/radiology/orders/`
- [ ] Try fetching radiology orders - should work
- [ ] Try creating a radiology order - should work
- [ ] Try fetching radiology results - should work
- [ ] Try creating a radiology result - should work
- [ ] Try viewing radiology order details - should work

## Status

✅ **All radiology endpoints fixed and components updated**


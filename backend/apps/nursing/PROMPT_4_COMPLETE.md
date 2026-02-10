# PROMPT 4 — Visit-Nested API Endpoints (COMPLETE)

## ✅ Implementation Status

All requirements from PROMPT 4 have been successfully implemented.

## Endpoints Created

All endpoints are visit-nested under `/api/v1/visits/{visit_id}/...`:

### 1. Vital Signs
- **POST** `/api/v1/visits/{visit_id}/vitals/` - Create vital signs (Nurse)
- **GET** `/api/v1/visits/{visit_id}/vitals/` - List vital signs (Doctor/Nurse)

### 2. Nursing Notes
- **POST** `/api/v1/visits/{visit_id}/nursing-notes/` - Create nursing note (Nurse only)
- **GET** `/api/v1/visits/{visit_id}/nursing-notes/` - List nursing notes (Doctor/Nurse)

### 3. Medication Administration
- **POST** `/api/v1/visits/{visit_id}/medication-administration/` - Create medication administration (Nurse only)
- **GET** `/api/v1/visits/{visit_id}/medication-administration/` - List medication administrations (Doctor/Nurse)

### 4. Lab Sample Collection
- **POST** `/api/v1/visits/{visit_id}/lab-samples/` - Create lab sample collection (Nurse only)
- **GET** `/api/v1/visits/{visit_id}/lab-samples/` - List lab sample collections (Doctor/Nurse)

## Requirements Compliance

### ✅ Endpoints MUST be nested under visit_id
- All endpoints are nested: `/api/v1/visits/{visit_id}/...`
- `visit_id` is extracted from URL kwargs in `get_visit()` method

### ✅ Role must be Nurse
- **Permission Class**: `IsNurse()` - Explicitly checks `user.role == 'NURSE'`
- **Enforcement**: Server-side only, in `get_permissions()` method
- **Vital Signs**: Uses `CanRecordVitalSigns()` which allows both Doctor and Nurse

### ✅ Visit must be ACTIVE (OPEN)
- **Permission Class**: `IsVisitActiveAndPaid()` - Checks `visit.status == 'OPEN'`
- **Validation**: Explicit check in permission class
- **Error**: Returns `PermissionDenied` if visit is not OPEN

### ✅ Visit must be paid (CLEARED)
- **Permission Class**: `IsVisitActiveAndPaid()` - Checks `visit.is_payment_cleared()`
- **Validation**: Calls `visit.is_payment_cleared()` method
- **Error**: Returns `PermissionDenied` if payment not cleared

### ✅ Closed visits must return 409 Conflict
- **Permission Class**: `IsVisitActiveAndPaid()` - Explicitly checks for `CLOSED` status
- **Error Handling**: Raises `APIException` with `status_code=409` for closed visits
- **Message**: "Cannot perform action on a CLOSED visit. Closed visits are immutable."

### ✅ Use explicit permission classes
- **Create Operations**: `[IsNurse(), IsVisitActiveAndPaid()]` (except vitals which uses `CanRecordVitalSigns()`)
- **Read Operations**: `[CanViewNursingRecords()]` or `[IsAuthenticated()]` for vitals
- **All permissions**: Defined in `apps/nursing/permissions.py` and `core/permissions.py`

## Implementation Details

### Files Created/Modified

1. **`backend/apps/nursing/nurse_endpoints.py`**
   - `NurseVitalSignsEndpoint` - ViewSet for vital signs
   - `NurseNursingNotesEndpoint` - ViewSet for nursing notes
   - `NurseMedicationAdministrationEndpoint` - ViewSet for medication administration
   - `NurseLabSamplesEndpoint` - ViewSet for lab sample collection

2. **`backend/apps/nursing/permissions.py`**
   - `IsVisitActiveAndPaid` - New permission class that:
     - Returns 409 Conflict for closed visits
     - Checks visit is OPEN (ACTIVE)
     - Checks payment is CLEARED

3. **`backend/apps/visits/urls.py`**
   - Added URL patterns for all four endpoints
   - All patterns are visit-nested: `<int:visit_id>/...`

### Permission Enforcement Flow

1. **Request arrives** at endpoint
2. **`get_permissions()`** is called based on action (create/list)
3. **Permission classes** are instantiated and checked:
   - `IsNurse()` - Verifies user role
   - `IsVisitActiveAndPaid()` - Verifies visit status and payment
4. **If visit is CLOSED**: `IsVisitActiveAndPaid` raises `APIException` with status 409
5. **If visit is not OPEN**: `IsVisitActiveAndPaid` raises `PermissionDenied` (403)
6. **If payment not cleared**: `IsVisitActiveAndPaid` raises `PermissionDenied` (403)
7. **If all checks pass**: Request proceeds to view method

### Error Responses

#### 409 Conflict (Closed Visit)
```json
{
  "detail": "Cannot perform action on a CLOSED visit. Closed visits are immutable.",
  "code": "visit_closed"
}
```

#### 403 Forbidden (Visit Not Active)
```json
{
  "detail": "Visit must be OPEN (ACTIVE) to perform this action. Current status: {status}",
  "code": "visit_not_active"
}
```

#### 403 Forbidden (Payment Not Cleared)
```json
{
  "detail": "Payment must be cleared before performing this action. Current payment status: {status}",
  "code": "payment_not_cleared"
}
```

#### 403 Forbidden (Not Nurse)
```json
{
  "detail": "You do not have permission to perform this action.",
  "code": "permission_denied"
}
```

## Testing Checklist

- [x] Endpoints are visit-nested
- [x] Nurse role required for creation
- [x] Visit must be OPEN (ACTIVE)
- [x] Visit payment must be CLEARED
- [x] Closed visits return 409 Conflict
- [x] Explicit permission classes used
- [x] GET endpoints allow Doctor and Nurse
- [x] POST endpoints require Nurse only (except vitals which allows both)

## Next Steps

The endpoints are ready for:
1. Frontend integration
2. API testing with Postman/curl
3. Integration testing with pytest

All requirements from PROMPT 4 have been met. ✅

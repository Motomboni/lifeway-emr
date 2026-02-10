# Visit Closure API - EMR Compliant Implementation

## Endpoint

```
POST /api/v1/visits/{id}/close/
```

## EMR Rule Compliance

✅ **Doctor-Only Closure**: Only doctors can close visits  
✅ **Consultation Required**: Visit must have at least one consultation  
✅ **Immutability Enforcement**: CLOSED visits cannot be modified  
✅ **DB-Level Validation**: Immutability enforced at database level  
✅ **API-Level Validation**: Immutability enforced at API level  
✅ **Audit Logging**: All closure actions logged to `AuditLog`  

## HTTP Methods

- **POST** `/api/v1/visits/{id}/close/` - Close visit (Doctor only)

## Role-Based Access Control

### Doctor
- ✅ **Can Close**: Visits (if consultation exists)
- ❌ **Cannot Modify**: CLOSED visits (immutability)

### Other Roles
- ❌ **Cannot Close**: Visits (only Doctor can)

## Validation Rules

1. **Consultation Required**: Visit must have at least one consultation
2. **Not Already Closed**: Visit must not already be CLOSED
3. **Doctor Only**: Only doctors can close visits
4. **Immutability**: CLOSED visits cannot be:
   - Modified (update/partial_update blocked)
   - Reopened (status cannot change from CLOSED to OPEN)
   - Have new orders created
   - Have new prescriptions created
   - Have new consultations created

## Request/Response Examples

### Close Visit (Doctor)

**Request:**
```http
POST /api/v1/visits/123/close/
Authorization: Token {doctor_token}
```

**Response:**
```json
{
    "message": "Visit closed successfully.",
    "visit": {
        "id": 123,
        "status": "CLOSED",
        "closed_by": 10,
        "closed_at": "2024-01-15T14:30:00Z"
    }
}
```

## Error Responses

### 400 Bad Request
- Visit does not have consultation
- Visit is already CLOSED

### 403 Forbidden
- User is not a doctor (on close)
- Attempting to modify CLOSED visit

### 404 Not Found
- Visit does not exist

## Immutability Enforcement

### Database Level
- Model `clean()` method prevents:
  - Changing status from CLOSED to OPEN
  - Closing visit without consultation
- ValidationError raised on save if rules violated

### API Level
- `update()` and `partial_update()` methods check visit status
- PermissionDenied raised if attempting to modify CLOSED visit
- All clinical endpoints (consultation, lab, radiology, prescriptions) check visit status

## Audit Logging

All visit closure actions are logged:

- **Action**: `visit.close`
- **User ID and Role**: Doctor who closed the visit
- **Visit ID**: Visit that was closed
- **IP Address**: IP address of the request
- **User Agent**: Device/browser fingerprint
- **Timestamp**: When the action occurred
- **Metadata**: Additional metadata (status, closed_by, closed_at)

## Test Cases

Comprehensive test suite covers:

1. **Authentication**: Unauthenticated access denied (401)
2. **Role Enforcement**: 
   - Receptionist cannot close (403)
   - Lab Tech cannot close (403)
   - Pharmacist cannot close (403)
   - Doctor can close (200)
3. **Consultation Enforcement**:
   - Cannot close without consultation (400)
   - Can close with consultation (200)
4. **Already Closed**: Cannot close already closed visit (400)
5. **Immutability**:
   - Cannot update CLOSED visit via API (403)
   - Cannot partially update CLOSED visit via API (403)
   - Cannot reopen CLOSED visit at DB level (ValidationError)
   - Cannot create new consultation for CLOSED visit (ValidationError)
   - Cannot create new orders for CLOSED visit (403)
   - Cannot create new prescriptions for CLOSED visit (403)
6. **Audit Logging**: Audit log created on successful closure
7. **Success Path**: Successful closure when all conditions met

## Failure Scenarios

1. **Close Nonexistent Visit**: 404 Not Found
2. **Close Without Consultation (DB Level)**: ValidationError
3. **Create Orders for CLOSED Visit**: 403 Forbidden
4. **Create Prescriptions for CLOSED Visit**: 403 Forbidden

## Security Considerations

1. **PHI Protection**: Visit information is PHI. Ensure:
   - Database encryption at rest
   - HTTPS in transit
   - No PHI in logs

2. **Immutability**: 
   - Enforced at both DB and API level
   - Prevents accidental or malicious modifications
   - Ensures audit trail integrity

3. **Role Separation**: 
   - Only doctors can close visits
   - Other roles explicitly blocked

## Compliance Checklist

✅ **Doctor-Only**: Only doctors can close visits  
✅ **Consultation Required**: Visit must have consultation  
✅ **Immutability DB**: Enforced at database level  
✅ **Immutability API**: Enforced at API level  
✅ **Audit Logging**: All actions logged  
✅ **Test Coverage**: All enforcement scenarios tested  
✅ **Failure Scenarios**: All failure cases covered  

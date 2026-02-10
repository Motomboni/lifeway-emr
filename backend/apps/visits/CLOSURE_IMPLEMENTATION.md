# Visit Closure Implementation - EMR Compliant

## Overview

Visit closure is a critical operation that makes a visit immutable. Once closed, no clinical actions can be performed on the visit.

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

## Implementation Details

### Model Level (`models.py`)

**Visit Model Enhancements:**
- Added `closed_by` (ForeignKey to User)
- Added `closed_at` (DateTimeField)
- Added `is_closed()` method
- Added `has_consultation()` method
- Enhanced `clean()` method with validation:
  - Prevents closing visit without consultation
  - Prevents changing status from CLOSED to OPEN
  - Prevents creating new visits with CLOSED status

**Validation Rules:**
1. Visit must have consultation before closure
2. Cannot change status from CLOSED to OPEN (immutability)
3. New visits cannot be created with CLOSED status

### API Level (`views.py`)

**VisitViewSet Enhancements:**
- Added `close()` action (POST method)
- Enhanced `update()` to block CLOSED visits
- Enhanced `partial_update()` to block CLOSED visits
- Added `check_user_role()` - ensures Doctor only
- Added `check_consultation_exists()` - ensures consultation exists
- Added `check_visit_not_already_closed()` - prevents double closure

**Enforcement Points:**
1. Doctor-only access (permission class + explicit check)
2. Consultation required (explicit validation)
3. Not already closed (explicit validation)
4. Immutability (blocks update/partial_update on CLOSED visits)

### Audit Logging

All closure actions are logged with:
- User ID and role
- Visit ID
- Action type (`visit.close`)
- IP address and user agent
- Timestamp
- Metadata (status, closed_by, closed_at)

## Immutability Enforcement

### Database Level

**Model Validation:**
```python
def clean(self):
    # Prevents closing without consultation
    if self.status == 'CLOSED' and self.pk:
        if old_visit.status == 'OPEN':
            if not self.has_consultation():
                raise ValidationError(...)
    
    # Prevents reopening
    if old_visit.status == 'CLOSED' and self.status == 'OPEN':
        raise ValidationError(...)
```

**Enforced on:**
- `save()` method (via `full_clean()`)
- All model operations that change status

### API Level

**ViewSet Methods:**
```python
def update(self, request, *args, **kwargs):
    visit = self.get_object()
    if visit.is_closed():
        raise PermissionDenied(...)
    return super().update(...)

def partial_update(self, request, *args, **kwargs):
    visit = self.get_object()
    if visit.is_closed():
        raise PermissionDenied(...)
    return super().partial_update(...)
```

**Enforced on:**
- PATCH `/api/v1/visits/{id}/`
- PUT `/api/v1/visits/{id}/`
- All clinical endpoints check visit status

## Test Coverage

### Authentication Tests
- ✅ Unauthenticated access denied (401)

### Role Enforcement Tests
- ✅ Receptionist cannot close (403)
- ✅ Lab Tech cannot close (403)
- ✅ Pharmacist cannot close (403)
- ✅ Doctor can close (200)

### Consultation Enforcement Tests
- ✅ Cannot close without consultation (400)
- ✅ Can close with consultation (200)

### Already Closed Tests
- ✅ Cannot close already closed visit (400)

### Immutability Tests
- ✅ Cannot update CLOSED visit via API (403)
- ✅ Cannot partially update CLOSED visit via API (403)
- ✅ Cannot reopen CLOSED visit at DB level (ValidationError)
- ✅ Cannot create new consultation for CLOSED visit (ValidationError)
- ✅ Cannot create new orders for CLOSED visit (403)
- ✅ Cannot create new prescriptions for CLOSED visit (403)

### Audit Logging Tests
- ✅ Audit log created on successful closure

### Success Path Tests
- ✅ Successful closure when all conditions met

### Failure Scenario Tests
- ✅ Close nonexistent visit (404)
- ✅ Close without consultation at DB level (ValidationError)
- ✅ Create orders for CLOSED visit (403)
- ✅ Create prescriptions for CLOSED visit (403)

## Failure Scenarios

1. **Close Without Consultation**
   - API: 400 Bad Request
   - DB: ValidationError on save

2. **Close Already Closed Visit**
   - API: 400 Bad Request

3. **Modify CLOSED Visit**
   - API: 403 Forbidden (update/partial_update)
   - DB: ValidationError on save (status change)

4. **Create Orders for CLOSED Visit**
   - API: 403 Forbidden (all clinical endpoints check visit status)

5. **Create Prescriptions for CLOSED Visit**
   - API: 403 Forbidden (all clinical endpoints check visit status)

## Security Considerations

1. **PHI Protection**: Visit information is PHI
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

## Files Modified/Created

- **`apps/visits/models.py`**: Enhanced Visit model with closure fields and validation
- **`apps/visits/views.py`**: Added VisitViewSet with close action
- **`apps/visits/urls.py`**: Updated URL configuration
- **`tests/security/test_visit_closure_enforcement.py`**: Comprehensive test suite
- **`tests/conftest.py`**: Added consultation fixture and updated closed_visit_with_payment fixture

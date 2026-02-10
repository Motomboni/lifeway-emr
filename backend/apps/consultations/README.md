# Consultation API - EMR Compliant Implementation

## Endpoint

```
/api/v1/visits/{visit_id}/consultation/
```

## EMR Rule Compliance

✅ **Visit-Scoped Architecture**: Endpoint is nested under `/visits/{visit_id}/`  
✅ **Doctor-Only Access**: Enforced via `IsDoctor` permission  
✅ **Visit Status Check**: Visit must be `OPEN` (enforced via `IsVisitOpen`)  
✅ **Payment Enforcement**: Payment must be `CLEARED` (enforced via `IsPaymentCleared`)  
✅ **Audit Logging**: All actions logged to `AuditLog`  
✅ **CLOSED Visit Rejection**: CLOSED visits are immutable  
✅ **No Standalone Endpoints**: Consultation cannot exist without Visit  

## HTTP Methods

- **GET** `/api/v1/visits/{visit_id}/consultation/` - Retrieve consultation (or empty list)
- **POST** `/api/v1/visits/{visit_id}/consultation/` - Create consultation
- **PUT** `/api/v1/visits/{visit_id}/consultation/` - Update consultation (full)
- **PATCH** `/api/v1/visits/{visit_id}/consultation/` - Update consultation (partial)
- **DELETE** `/api/v1/visits/{visit_id}/consultation/` - **DISABLED** (compliance requirement)

## Middleware Assumptions

The implementation assumes the following middleware stack (in order):

1. **Authentication Middleware** (Django/DRF)
   - JWT token validation
   - User authentication
   - Sets `request.user`

2. **VisitLookupMiddleware** (`core.middleware.visit_lookup`)
   - Extracts `visit_id` from URL
   - Fetches `Visit` object
   - Attaches `request.visit` and `request.visit_id`
   - **Required**: Must run before payment/role guards

3. **PaymentClearedGuard** (`core.middleware.payment_guard`)
   - Checks `request.visit.is_payment_cleared()`
   - Raises `PermissionDenied` if payment not cleared
   - **Required**: Must run after `VisitLookupMiddleware`

4. **RoleGuard** (if exists)
   - Validates user role
   - **Optional**: ViewSet also enforces via permissions

## Permission Classes

- **IsDoctor**: Ensures user role is `DOCTOR`
  - Assumes `User.role == 'DOCTOR'` or `User.get_role() == 'DOCTOR'`
  
- **IsVisitOpen**: Ensures `request.visit.status == 'OPEN'`
  - Requires `VisitLookupMiddleware` to set `request.visit`
  
- **IsPaymentCleared**: Ensures `request.visit.is_payment_cleared()`
  - Requires `VisitLookupMiddleware` to set `request.visit`
  - Redundant with `PaymentClearedGuard` but provides defense-in-depth

## Audit Logging

All consultation actions are logged to `AuditLog`:

- **create**: When consultation is created
- **update**: When consultation is updated
- **read**: When consultation is retrieved

Audit log includes:
- User ID and role
- Action type
- Visit ID
- Consultation ID
- IP address
- User agent
- Timestamp

## Error Responses

### 401 Unauthorized
- Missing or invalid JWT token
- User not authenticated

### 403 Forbidden
- User is not a doctor (`IsDoctor` fails)
- Visit is CLOSED (`IsVisitOpen` fails)
- Payment not cleared (`IsPaymentCleared` fails)

### 404 Not Found
- Visit does not exist
- Consultation not found for visit (on GET)

### 400 Bad Request
- Validation errors
- Consultation already exists (on POST)

### 409 Conflict
- Attempting to modify CLOSED visit

## User Model Assumptions

The implementation assumes the User model has:

```python
class User(AbstractUser):
    role = models.CharField(max_length=50)  # 'DOCTOR', 'NURSE', etc.
    # OR
    def get_role(self):
        return self.role  # or custom logic
```

## Visit Model Assumptions

The implementation assumes the Visit model has:

```python
class Visit(models.Model):
    status = models.CharField(max_length=20, default='OPEN')  # 'OPEN', 'CLOSED'
    payment_status = models.CharField(max_length=20, default='PENDING')  # 'PENDING', 'CLEARED'
    
    def is_payment_cleared(self):
        return self.payment_status == 'CLEARED'
```

## Settings Configuration

Add to `MIDDLEWARE` in `settings.py`:

```python
MIDDLEWARE = [
    # ... other middleware ...
    'core.middleware.visit_lookup.VisitLookupMiddleware',
    'core.middleware.payment_guard.PaymentClearedGuard',
    # ... rest of middleware ...
]
```

## Testing

The implementation is designed to pass all security tests:

- ✅ A1: Unauthenticated access → 401
- ✅ A2: Expired token → 401
- ✅ B1: Receptionist attempting consultation → 403
- ✅ C1: Cross-visit access → 403 (if visit ownership enforced)
- ✅ C2: Closed visit mutation → 403/409
- ✅ D1: Consultation before payment → 403/402

## Compliance Notes

1. **PHI Protection**: All consultation fields are PHI. Ensure:
   - Database encryption at rest
   - HTTPS in transit
   - No PHI in logs (audit logs use IDs only)

2. **Audit Log Integrity**: 
   - `AuditLog.save()` prevents updates
   - `AuditLog.delete()` prevents deletion
   - Append-only by design

3. **Soft Delete**: 
   - DELETE endpoint is disabled
   - Use soft-delete pattern if needed

4. **Data Minimization**: 
   - Serializer only returns required fields
   - No patient details exposed (only visit_id)

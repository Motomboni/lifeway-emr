# Visit Closure Rules

## Overview

This document describes the billing validation rules for visit closure in the EMR system.

## Endpoint

**POST** `/api/v1/visits/{id}/close/`

**Authentication:** Required (Doctor only)

## Closure Rules

### 1. Doctor-Only Closure
- Only users with `DOCTOR` role can close visits
- Other roles receive `403 Forbidden` error

### 2. Consultation Required
- Visit must have at least one consultation before closure
- Returns `400 Bad Request` if no consultation exists

### 3. Visit Not Already Closed
- Visit must be in `OPEN` status
- Returns `400 Bad Request` if visit is already `CLOSED`

### 4. Billing Validation

#### CASH Visit Rules
- **Requirement**: Bill outstanding balance must be 0
- **Validation**: Checks `Bill.outstanding_balance == 0`
- **Error Message**: 
  ```
  Cannot close CASH visit with outstanding balance. 
  Outstanding balance: ₦X,XXX.XX. 
  Please ensure all payments are processed before closing the visit.
  ```

#### INSURANCE Visit Rules
- **Requirement**: Bill status must be `INSURANCE_PENDING` or `SETTLED`
- **Validation**: Checks `Bill.status in ['INSURANCE_PENDING', 'SETTLED']`
- **Error Message**:
  ```
  Cannot close INSURANCE visit. Bill status is '{status}'. 
  Bill status must be 'INSURANCE_PENDING' or 'SETTLED' to close the visit. 
  Current bill status: {display_name}
  ```

## Validation Flow

```
1. Check user is Doctor → 403 if not
2. Check visit is OPEN → 400 if CLOSED
3. Check consultation exists → 400 if none
4. Check billing rules:
   - If CASH: outstanding_balance == 0
   - If INSURANCE: status in [INSURANCE_PENDING, SETTLED]
5. Close visit → 200 on success
```

## Error Responses

### 403 Forbidden (Not a Doctor)
```json
{
    "detail": "Only doctors can close visits."
}
```

### 400 Bad Request (No Consultation)
```json
{
    "detail": "Visit must have at least one consultation before it can be closed."
}
```

### 400 Bad Request (Already Closed)
```json
{
    "detail": "Visit is already CLOSED. Closed visits are immutable per EMR rules."
}
```

### 400 Bad Request (CASH Visit - Outstanding Balance)
```json
{
    "detail": "Cannot close CASH visit with outstanding balance. Outstanding balance: ₦5,000.00. Please ensure all payments are processed before closing the visit.",
    "visit_id": 1,
    "payment_type": "CASH"
}
```

### 400 Bad Request (INSURANCE Visit - Invalid Status)
```json
{
    "detail": "Cannot close INSURANCE visit. Bill status is 'UNPAID'. Bill status must be 'INSURANCE_PENDING' or 'SETTLED' to close the visit. Current bill status: Unpaid",
    "visit_id": 1,
    "payment_type": "INSURANCE"
}
```

## Success Response

### 200 OK
```json
{
    "message": "Visit closed successfully.",
    "visit": {
        "id": 1,
        "status": "CLOSED",
        "closed_by": 10,
        "closed_at": "2024-01-15T14:30:00Z"
    }
}
```

## Examples

### Example 1: Close CASH Visit with Outstanding Balance

**Request:**
```http
POST /api/v1/visits/1/close/
Authorization: Bearer <doctor_token>
```

**Response (400):**
```json
{
    "detail": "Cannot close CASH visit with outstanding balance. Outstanding balance: ₦5,000.00. Please ensure all payments are processed before closing the visit.",
    "visit_id": 1,
    "payment_type": "CASH"
}
```

**Action Required:**
- Process payment of ₦5,000.00
- Retry visit closure

### Example 2: Close CASH Visit with Zero Balance

**Request:**
```http
POST /api/v1/visits/1/close/
Authorization: Bearer <doctor_token>
```

**Response (200):**
```json
{
    "message": "Visit closed successfully.",
    "visit": {
        "id": 1,
        "status": "CLOSED",
        "closed_by": 10,
        "closed_at": "2024-01-15T14:30:00Z"
    }
}
```

### Example 3: Close INSURANCE Visit with Invalid Status

**Request:**
```http
POST /api/v1/visits/2/close/
Authorization: Bearer <doctor_token>
```

**Response (400):**
```json
{
    "detail": "Cannot close INSURANCE visit. Bill status is 'UNPAID'. Bill status must be 'INSURANCE_PENDING' or 'SETTLED' to close the visit. Current bill status: Unpaid",
    "visit_id": 2,
    "payment_type": "INSURANCE"
}
```

**Action Required:**
- Submit insurance claim (status → INSURANCE_PENDING)
- Or wait for insurance settlement (status → SETTLED)
- Retry visit closure

### Example 4: Close INSURANCE Visit with Valid Status

**Request:**
```http
POST /api/v1/visits/2/close/
Authorization: Bearer <doctor_token>
```

**Response (200):**
```json
{
    "message": "Visit closed successfully.",
    "visit": {
        "id": 2,
        "status": "CLOSED",
        "closed_by": 10,
        "closed_at": "2024-01-15T14:30:00Z"
    }
}
```

## Bill Status Flow

### CASH Visit Flow
```
UNPAID → PARTIALLY_PAID → PAID
         ↓
    outstanding_balance == 0
         ↓
    Visit can be closed
```

### INSURANCE Visit Flow
```
UNPAID → INSURANCE_PENDING → INSURANCE_CLAIMED → SETTLED
         ↓                                    ↓
    Visit can be closed              Visit can be closed
```

## Implementation Details

### BillingService.can_close_visit()

```python
@staticmethod
def can_close_visit(visit) -> tuple[bool, str]:
    """
    Check if a Visit can be closed based on billing.
    
    Rules:
    - If CASH visit: Bill outstanding balance must be 0
    - If INSURANCE visit: Bill status must be INSURANCE_PENDING or SETTLED
    
    Returns:
        tuple: (can_close: bool, reason: str)
    """
```

### VisitViewSet.close()

```python
@action(detail=True, methods=['post'], url_path='close')
def close(self, request, pk=None):
    """
    Close a visit.
    
    Validation:
    1. Doctor-only
    2. Consultation exists
    3. Visit is OPEN
    4. Billing rules:
       - CASH: outstanding_balance == 0
       - INSURANCE: status in [INSURANCE_PENDING, SETTLED]
    """
```

## Testing

### Test Cases

1. **CASH Visit - Outstanding Balance > 0**
   - Expected: 400 Bad Request
   - Message: Outstanding balance error

2. **CASH Visit - Outstanding Balance == 0**
   - Expected: 200 OK
   - Visit closed successfully

3. **INSURANCE Visit - Status UNPAID**
   - Expected: 400 Bad Request
   - Message: Invalid status error

4. **INSURANCE Visit - Status INSURANCE_PENDING**
   - Expected: 200 OK
   - Visit closed successfully

5. **INSURANCE Visit - Status SETTLED**
   - Expected: 200 OK
   - Visit closed successfully

6. **Non-Doctor User**
   - Expected: 403 Forbidden
   - Message: Only doctors can close visits

7. **No Consultation**
   - Expected: 400 Bad Request
   - Message: Consultation required

8. **Already Closed**
   - Expected: 400 Bad Request
   - Message: Already closed

## Best Practices

1. **Check Bill Status Before Closure**
   - Receptionist should verify bill status before doctor attempts closure
   - Display bill status in visit details UI

2. **Process Payments First**
   - For CASH visits, ensure all payments are processed
   - For INSURANCE visits, ensure claim is submitted or settled

3. **Clear Error Messages**
   - Error messages include specific amounts and statuses
   - Actionable guidance provided in error messages

4. **Audit Logging**
   - All closure attempts are logged
   - Failed closures include reason in audit log

## Related Documentation

- `BILLING_SERVICE.md` - Billing service documentation
- `CLOSURE_IMPLEMENTATION.md` - General closure implementation
- `BILL_MODELS_DOCUMENTATION.md` - Bill model documentation


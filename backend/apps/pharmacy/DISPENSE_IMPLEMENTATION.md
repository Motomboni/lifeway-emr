# Pharmacy Dispensing API Implementation

## Endpoint

```
POST /api/v1/visits/{visit_id}/pharmacy/dispense/
```

## EMR Rule Compliance

✅ **Visit-Scoped Architecture**: Endpoint is nested under `/visits/{visit_id}/`  
✅ **Prescription-Dependent**: Dispensing requires prescription to exist  
✅ **Pharmacist-Only**: Only Pharmacists can dispense medication  
✅ **Doctor Cannot Dispense**: Doctors are explicitly blocked  
✅ **Payment Enforcement**: Payment must be `CLEARED`  
✅ **Visit Status Check**: Visit must be `OPEN`  
✅ **Audit Logging**: All actions logged to `AuditLog`  

## Request Format

**Request Body:**
```json
{
    "prescription_id": 1,
    "dispensing_notes": "Dispensed as prescribed. Patient counseled on side effects."
}
```

**Required Fields:**
- `prescription_id` (integer, required): ID of the prescription to dispense

**Optional Fields:**
- `dispensing_notes` (string, optional): Notes from pharmacist during dispensing

## Response Format

**Success Response (200 OK):**
```json
{
    "message": "Medication dispensed successfully.",
    "prescription": {
        "id": 1,
        "visit_id": 123,
        "consultation_id": 45,
        "drug": "Amoxicillin",
        "dosage": "500mg",
        "status": "DISPENSED",
        "dispensed": true,
        "dispensed_date": "2024-01-15T14:30:00Z",
        "dispensing_notes": "Dispensed as prescribed. Patient counseled on side effects.",
        "prescribed_by": 10,
        "dispensed_by": 17,
        ...
    }
}
```

## Role Enforcement

### Pharmacist
- ✅ **Can Dispense**: Medication for prescriptions
- ❌ **Cannot Create**: Prescriptions (only Doctor can)

### Doctor
- ❌ **Cannot Dispense**: Medication (only Pharmacist can)
- ✅ **Can Create**: Prescriptions
- ✅ **Can View**: All prescription fields

## Validation Rules

1. **Prescription Required**: `prescription_id` must be provided in request body
2. **Prescription Exists**: Prescription must exist and belong to the visit
3. **Not Already Dispensed**: Prescription must not already be dispensed
4. **Not Cancelled**: Prescription must not be cancelled
5. **Payment Cleared**: Payment must be CLEARED before dispensing
6. **Visit Open**: Visit must be OPEN (not CLOSED) for dispensing

## Error Responses

### 400 Bad Request
- Missing `prescription_id` in request body
- Prescription already dispensed
- Prescription is cancelled

### 403 Forbidden
- User is not a Pharmacist (on dispense)
- Payment not cleared
- Visit is CLOSED

### 404 Not Found
- Visit does not exist
- Prescription not found for visit

## Audit Logging

All dispensing actions are logged:

- **Action**: `pharmacy.dispense`
- **User ID and Role**: Pharmacist who dispensed
- **Visit ID**: Visit associated with prescription
- **Prescription ID**: Prescription that was dispensed
- **IP Address**: IP address of the request
- **User Agent**: Device/browser fingerprint
- **Timestamp**: When the action occurred
- **Metadata**: Additional metadata (drug name, status)

## Test Cases

Comprehensive test suite covers:

1. **Authentication**: Unauthenticated access denied (401)
2. **Role Enforcement**: 
   - Doctor cannot dispense (403)
   - Receptionist cannot dispense (403)
   - Pharmacist can dispense (200)
3. **Prescription Enforcement**:
   - Missing prescription_id (400)
   - Nonexistent prescription (404)
   - Already dispensed prescription (400)
   - Cancelled prescription (400)
4. **Payment Enforcement**: Payment PENDING blocks dispensing (403)
5. **Visit Status Enforcement**: CLOSED visit blocks dispensing (403)
6. **Audit Logging**: Audit log created on successful dispense
7. **Success Path**: Successful dispensing when all conditions met

## Implementation Files

- **`dispense_views.py`**: ViewSet for dispensing endpoint
- **`dispense_urls.py`**: URL configuration for dispensing
- **`permissions.py`**: `CanDispensePrescription` permission class
- **`test_pharmacy_dispense_enforcement.py`**: Comprehensive test suite

## Security Considerations

1. **PHI Protection**: Prescription information is PHI. Ensure:
   - Database encryption at rest
   - HTTPS in transit
   - No PHI in logs

2. **Role Separation**: 
   - Doctor cannot dispense
   - Pharmacist cannot create prescriptions
   - Strict role boundaries enforced

3. **Data Integrity**:
   - Prescription must belong to visit
   - Cannot dispense already dispensed prescription
   - Cannot dispense cancelled prescription

## Compliance Checklist

✅ **Visit-Scoped**: Endpoint nested under `/visits/{visit_id}/`  
✅ **Prescription-Dependent**: Dispensing requires prescription  
✅ **Pharmacist-Only**: Only Pharmacists can dispense  
✅ **Doctor Blocked**: Doctors explicitly cannot dispense  
✅ **Payment Enforcement**: Payment must be CLEARED  
✅ **Visit Status**: Visit must be OPEN  
✅ **Audit Logging**: All actions logged  
✅ **Validation**: Comprehensive validation rules  
✅ **Test Coverage**: All enforcement scenarios tested  

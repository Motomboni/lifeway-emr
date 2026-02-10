# Prescription API - EMR Compliant Implementation

## Endpoint

```
/api/v1/visits/{visit_id}/prescriptions/
```

## EMR Rule Compliance

✅ **Visit-Scoped Architecture**: Endpoint is nested under `/visits/{visit_id}/`  
✅ **Consultation-Dependent**: Prescriptions REQUIRE consultation context  
✅ **Doctor-Only Creation**: Only doctors can create prescriptions  
✅ **Payment Enforcement**: Payment must be `CLEARED`  
✅ **Visit Status Check**: Visit must be `OPEN` for mutations  
✅ **Audit Logging**: All actions logged to `AuditLog`  
✅ **No Standalone Flow**: Prescriptions cannot exist without consultation  

## HTTP Methods

- **GET** `/api/v1/visits/{visit_id}/prescriptions/` - List prescriptions (role-based fields)
- **GET** `/api/v1/visits/{visit_id}/prescriptions/{id}/` - Retrieve prescription (role-based fields)
- **POST** `/api/v1/visits/{visit_id}/prescriptions/` - Create prescription (Doctor only)
- **PATCH** `/api/v1/visits/{visit_id}/prescriptions/{id}/` - Update prescription (Pharmacist only - dispense)
- **PUT** `/api/v1/visits/{visit_id}/prescriptions/{id}/` - Update prescription (Pharmacist only - dispense)
- **DELETE** `/api/v1/visits/{visit_id}/prescriptions/{id}/` - **DISABLED** (compliance requirement)

## Role-Based Access Control

### Doctor
- ✅ **Can Create**: Prescriptions
- ✅ **Can View**: All fields including dispensing information
- ❌ **Cannot Update**: Prescriptions (only Pharmacist can dispense)
- ❌ **Cannot Delete**: Prescriptions

### Pharmacist
- ❌ **Cannot Create**: Prescriptions (only Doctor can)
- ✅ **Can View**: Limited fields (no consultation details)
- ✅ **Can Update**: Dispense medication only
- ❌ **Cannot Delete**: Prescriptions

## Data Visibility Rules

### Doctor Sees:
- All prescription fields
- Drug, dosage, frequency, duration, quantity, instructions
- Dispensing status and notes
- Consultation context
- Prescription history

### Pharmacist Sees:
- Drug, dosage, frequency, duration, quantity, instructions (read-only)
- Status
- Dispensing fields (can update)
- Prescribed by (read-only)
- **Cannot See**: Consultation details, diagnosis, patient history

## Request/Response Examples

### Create Prescription (Doctor)

**Request:**
```http
POST /api/v1/visits/123/prescriptions/
Authorization: Token {doctor_token}
Content-Type: application/json

{
  "drug": "Amoxicillin",
  "drug_code": "AMX-500",
  "dosage": "500mg",
  "frequency": "TID",
  "duration": "7 days",
  "quantity": "21 tablets",
  "instructions": "Take with food"
}
```

**Response:**
```json
{
  "id": 1,
  "visit_id": 123,
  "consultation_id": 45,
  "drug": "Amoxicillin",
  "drug_code": "AMX-500",
  "dosage": "500mg",
  "frequency": "TID",
  "duration": "7 days",
  "quantity": "21 tablets",
  "instructions": "Take with food",
  "status": "PENDING",
  "dispensed": false,
  "dispensed_date": null,
  "dispensing_notes": "",
  "prescribed_by": 10,
  "dispensed_by": null,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Dispense Prescription (Pharmacist)

**Request:**
```http
PATCH /api/v1/visits/123/prescriptions/1/
Authorization: Token {pharmacist_token}
Content-Type: application/json

{
  "dispensed": true,
  "dispensing_notes": "Dispensed as prescribed. Patient counseled on side effects."
}
```

**Response:**
```json
{
  "id": 1,
  "visit_id": 123,
  "consultation_id": 45,
  "drug": "Amoxicillin",
  "drug_code": "AMX-500",
  "dosage": "500mg",
  "frequency": "TID",
  "duration": "7 days",
  "quantity": "21 tablets",
  "instructions": "Take with food",
  "status": "DISPENSED",
  "dispensed": true,
  "dispensed_date": "2024-01-15T14:30:00Z",
  "dispensing_notes": "Dispensed as prescribed. Patient counseled on side effects.",
  "prescribed_by": 10,
  "dispensed_by": 17,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T14:30:00Z"
}
```

## Error Responses

### 400 Bad Request
- Consultation does not exist
- Validation errors
- Missing required fields

### 403 Forbidden
- User is not a doctor (on create)
- User is not a pharmacist (on update/dispense)
- Payment not cleared
- Visit is CLOSED

### 404 Not Found
- Visit does not exist
- Prescription not found

### 409 Conflict
- Attempting to modify CLOSED visit

## Validation Rules

1. **Consultation Required**: Prescription cannot be created without consultation
2. **Visit Match**: Consultation must belong to the same visit
3. **Payment Cleared**: Payment must be CLEARED before creating prescriptions
4. **Visit Open**: Visit must be OPEN (not CLOSED) for mutations
5. **Drug Required**: Drug name is required
6. **Dosage Required**: Dosage is required

## Audit Logging

All prescription actions are logged:

- **create**: When doctor creates prescription
- **dispense**: When pharmacist dispenses medication
- **read**: When prescription is viewed

Audit log includes:
- User ID and role
- Action type
- Visit ID
- Prescription ID
- IP address
- User agent
- Timestamp

## Security Considerations

1. **PHI Protection**: Prescription information is PHI. Ensure:
   - Database encryption at rest
   - HTTPS in transit
   - No PHI in logs

2. **Role Separation**: 
   - Doctor cannot dispense
   - Pharmacist cannot create prescriptions
   - Strict role boundaries enforced

3. **Data Minimization**:
   - Pharmacist sees only necessary fields
   - No consultation details exposed to Pharmacist
   - Diagnosis not visible to Pharmacist

## Testing

The implementation is designed to pass all security tests:

- ✅ Pharmacist cannot create prescriptions → 403
- ✅ Doctor cannot dispense → 403
- ✅ Prescription without consultation → 400
- ✅ Prescription with payment PENDING → 403
- ✅ Prescription for CLOSED visit → 403
- ✅ Audit log created on all actions
- ✅ Role-based field visibility verified

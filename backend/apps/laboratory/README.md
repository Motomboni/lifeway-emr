# Lab Order API - EMR Compliant Implementation

## Endpoint

```
/api/v1/visits/{visit_id}/laboratory/
```

## EMR Rule Compliance

✅ **Visit-Scoped Architecture**: Endpoint is nested under `/visits/{visit_id}/`  
✅ **Consultation-Dependent**: Lab orders REQUIRE consultation context  
✅ **Doctor-Only Creation**: Only doctors can create lab orders  
✅ **Lab Tech-Only Results**: Only Lab Tech can post results  
✅ **Payment Enforcement**: Payment must be `CLEARED`  
✅ **Visit Status Check**: Visit must be `OPEN`  
✅ **Audit Logging**: All actions logged to `AuditLog`  
✅ **No Standalone Flow**: Lab orders cannot exist without consultation  

## HTTP Methods

- **GET** `/api/v1/visits/{visit_id}/laboratory/` - List lab orders (role-based fields)
- **GET** `/api/v1/visits/{visit_id}/laboratory/{id}/` - Retrieve lab order (role-based fields)
- **POST** `/api/v1/visits/{visit_id}/laboratory/` - Create lab order (Doctor only)
- **PATCH** `/api/v1/visits/{visit_id}/laboratory/{id}/` - Update result (Lab Tech only)
- **PUT** `/api/v1/visits/{visit_id}/laboratory/{id}/` - Update result (Lab Tech only)
- **DELETE** `/api/v1/visits/{visit_id}/laboratory/{id}/` - **DISABLED** (compliance requirement)

## Role-Based Access Control

### Doctor
- ✅ **Can Create**: Lab orders
- ✅ **Can View**: All fields including results
- ❌ **Cannot Update**: Results (only Lab Tech can)
- ❌ **Cannot Delete**: Lab orders

### Lab Tech
- ❌ **Cannot Create**: Lab orders (only Doctor can)
- ✅ **Can View**: Limited fields (no consultation details)
- ✅ **Can Update**: Results only
- ❌ **Cannot Delete**: Lab orders

## Data Visibility Rules

### Doctor Sees:
- All lab order fields
- Test name, code, instructions
- Results (when available)
- Consultation context
- Order history

### Lab Tech Sees:
- Test name, code, instructions (read-only)
- Status
- Result field (can update)
- Ordered by (read-only)
- **Cannot See**: Consultation details, diagnosis, patient history

## Request/Response Examples

### Create Lab Order (Doctor)

**Request:**
```http
POST /api/v1/visits/123/laboratory/
Authorization: Token {doctor_token}
Content-Type: application/json

{
  "test_name": "Complete Blood Count",
  "test_code": "CBC",
  "instructions": "Fasting required"
}
```

**Response:**
```json
{
  "id": 1,
  "visit_id": 123,
  "consultation_id": 45,
  "test_name": "Complete Blood Count",
  "test_code": "CBC",
  "instructions": "Fasting required",
  "status": "PENDING",
  "result": null,
  "result_date": null,
  "ordered_by": 10,
  "resulted_by": null,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Update Result (Lab Tech)

**Request:**
```http
PATCH /api/v1/visits/123/laboratory/1/
Authorization: Token {lab_tech_token}
Content-Type: application/json

{
  "result": "WBC: 7.2, RBC: 4.5, HGB: 14.2, PLT: 250",
  "status": "COMPLETED"
}
```

**Response:**
```json
{
  "id": 1,
  "visit_id": 123,
  "consultation_id": 45,
  "test_name": "Complete Blood Count",
  "test_code": "CBC",
  "instructions": "Fasting required",
  "status": "COMPLETED",
  "result": "WBC: 7.2, RBC: 4.5, HGB: 14.2, PLT: 250",
  "result_date": "2024-01-15T14:30:00Z",
  "ordered_by": 10,
  "resulted_by": 15,
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
- User is not a lab tech (on update result)
- Payment not cleared
- Visit is CLOSED

### 404 Not Found
- Visit does not exist
- Lab order not found

### 409 Conflict
- Attempting to modify CLOSED visit

## Validation Rules

1. **Consultation Required**: Lab order cannot be created without consultation
2. **Visit Match**: Consultation must belong to the same visit
3. **Payment Cleared**: Payment must be CLEARED before creating lab orders
4. **Visit Open**: Visit must be OPEN (not CLOSED)
5. **Result Required**: Lab Tech must provide result when status is COMPLETED

## Audit Logging

All lab order actions are logged:

- **create**: When doctor creates lab order
- **update_result**: When lab tech posts result
- **read**: When lab order is viewed

Audit log includes:
- User ID and role
- Action type
- Visit ID
- Lab Order ID
- IP address
- User agent
- Timestamp

## Security Considerations

1. **PHI Protection**: Lab results are PHI. Ensure:
   - Database encryption at rest
   - HTTPS in transit
   - No PHI in logs

2. **Role Separation**: 
   - Doctor cannot post results
   - Lab Tech cannot create orders
   - Strict role boundaries enforced

3. **Data Minimization**:
   - Lab Tech sees only necessary fields
   - No consultation details exposed to Lab Tech
   - Diagnosis not visible to Lab Tech

## Testing

The implementation is designed to pass all security tests:

- ✅ B2: Lab Tech cannot create lab orders → 403
- ✅ Role separation enforced
- ✅ Consultation dependency enforced
- ✅ Payment enforcement
- ✅ Visit status enforcement
- ✅ Audit logging verified

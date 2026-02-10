# Radiology Request API - EMR Compliant Implementation

## Service Catalog vs Legacy Flow

- **RadiologyRequest** is the **single source of truth** for Service Catalog radiology orders. All reports for this flow are stored directly on `RadiologyRequest` (report, report_date, reported_by, image_count). **Do not create RadiologyResult for Service Catalog orders.**
- **RadiologyResult** is used only for the legacy **RadiologyOrder** flow (RadiologyOrder → RadiologyResult). Service Catalog orders use RadiologyRequest only.

## Endpoint

```
/api/v1/visits/{visit_id}/radiology/
```

## EMR Rule Compliance

✅ **Visit-Scoped Architecture**: Endpoint is nested under `/visits/{visit_id}/`  
✅ **Consultation-Dependent**: Radiology requests REQUIRE consultation context  
✅ **Doctor-Only Creation**: Only doctors can create radiology requests  
✅ **Radiology Tech-Only Reports**: Only Radiology Tech can post reports  
✅ **Payment Enforcement**: Payment must be `CLEARED`  
✅ **Visit Status Check**: Visit must be `OPEN` for mutations  
✅ **Audit Logging**: All actions logged to `AuditLog`  
✅ **No Standalone Flow**: Radiology requests cannot exist without consultation  
✅ **Status**: `PENDING` | `COMPLETED` only (no IN_PROGRESS/CANCELLED for Service Catalog)  

## HTTP Methods

- **GET** `/api/v1/visits/{visit_id}/radiology/` - List radiology requests (role-based fields)
- **GET** `/api/v1/visits/{visit_id}/radiology/{id}/` - Retrieve radiology request (role-based fields)
- **POST** `/api/v1/visits/{visit_id}/radiology/` - Create radiology request (Doctor only)
- **PATCH** `/api/v1/visits/{visit_id}/radiology/{id}/` - Update report (Radiology Tech only)
- **PUT** `/api/v1/visits/{visit_id}/radiology/{id}/` - Update report (Radiology Tech only)
- **DELETE** `/api/v1/visits/{visit_id}/radiology/{id}/` - **DISABLED** (compliance requirement)

## Role-Based Access Control

### Doctor
- ✅ **Can Create**: Radiology requests
- ✅ **Can View**: All fields including reports
- ❌ **Cannot Update**: Reports (only Radiology Tech can)
- ❌ **Cannot Delete**: Radiology requests

### Radiology Tech
- ❌ **Cannot Create**: Radiology requests (only Doctor can)
- ✅ **Can View**: Limited fields (no consultation details)
- ✅ **Can Update**: Reports only
- ❌ **Cannot Delete**: Radiology requests

## Data Visibility Rules

### Doctor Sees:
- All radiology request fields
- Study type, code, clinical indication, instructions
- Reports (when available)
- Image metadata
- Consultation context
- Request history

### Radiology Tech Sees:
- Study type, code, clinical indication, instructions (read-only)
- Status
- Report field (can update)
- Image count and metadata (can update)
- Ordered by (read-only)
- **Cannot See**: Consultation details, diagnosis, patient history

## Request/Response Examples

### Create Radiology Request (Doctor)

**Request:**
```http
POST /api/v1/visits/123/radiology/
Authorization: Token {doctor_token}
Content-Type: application/json

{
  "study_type": "Chest X-Ray",
  "study_code": "CXR",
  "clinical_indication": "Suspected pneumonia",
  "instructions": "PA and lateral views"
}
```

**Response:**
```json
{
  "id": 1,
  "visit_id": 123,
  "consultation_id": 45,
  "study_type": "Chest X-Ray",
  "study_code": "CXR",
  "clinical_indication": "Suspected pneumonia",
  "instructions": "PA and lateral views",
  "status": "PENDING",
  "report": null,
  "report_date": null,
  "image_count": null,
  "image_metadata": {},
  "ordered_by": 10,
  "reported_by": null,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Update Report (Radiology Tech)

**Request:**
```http
PATCH /api/v1/visits/123/radiology/1/
Authorization: Token {radiology_tech_token}
Content-Type: application/json

{
  "report": "No acute cardiopulmonary process. Lungs are clear. Heart size normal.",
  "status": "COMPLETED",
  "image_count": 2,
  "image_metadata": {
    "modality": "CR",
    "series": ["PA", "Lateral"],
    "slices": 2
  }
}
```

**Response:**
```json
{
  "id": 1,
  "visit_id": 123,
  "consultation_id": 45,
  "study_type": "Chest X-Ray",
  "study_code": "CXR",
  "clinical_indication": "Suspected pneumonia",
  "instructions": "PA and lateral views",
  "status": "COMPLETED",
  "report": "No acute cardiopulmonary process. Lungs are clear. Heart size normal.",
  "report_date": "2024-01-15T14:30:00Z",
  "image_count": 2,
  "image_metadata": {
    "modality": "CR",
    "series": ["PA", "Lateral"],
    "slices": 2
  },
  "ordered_by": 10,
  "reported_by": 16,
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
- User is not a radiology tech (on update report)
- Payment not cleared
- Visit is CLOSED

### 404 Not Found
- Visit does not exist
- Radiology request not found

### 409 Conflict
- Attempting to modify CLOSED visit

## Validation Rules

1. **Consultation Required**: Radiology request cannot be created without consultation
2. **Visit Match**: Consultation must belong to the same visit
3. **Payment Cleared**: Payment must be CLEARED before creating radiology requests
4. **Visit Open**: Visit must be OPEN (not CLOSED) for mutations
5. **Report Required**: Radiology Tech must provide report when status is COMPLETED

## Audit Logging

All radiology request actions are logged:

- **create**: When doctor creates radiology request
- **update_report**: When radiology tech posts report
- **read**: When radiology request is viewed

Audit log includes:
- User ID and role
- Action type
- Visit ID
- Radiology Request ID
- IP address
- User agent
- Timestamp

## Image Metadata

Image metadata is stored as JSON and includes:
- Modality (e.g., "CR", "CT", "MRI")
- Series information
- Number of slices/images
- **No raw DICOM data** (per requirements)

Example:
```json
{
  "modality": "CT",
  "series": ["Axial", "Coronal", "Sagittal"],
  "slices": 120,
  "slice_thickness": "1mm"
}
```

## Security Considerations

1. **PHI Protection**: Radiology reports are PHI. Ensure:
   - Database encryption at rest
   - HTTPS in transit
   - No PHI in logs

2. **Role Separation**: 
   - Doctor cannot post reports
   - Radiology Tech cannot create requests
   - Strict role boundaries enforced

3. **Data Minimization**:
   - Radiology Tech sees only necessary fields
   - No consultation details exposed to Radiology Tech
   - Diagnosis not visible to Radiology Tech

## Testing

The implementation is designed to pass all security tests:

- ✅ Radiology Tech cannot create requests → 403
- ✅ Doctor cannot update reports → 403
- ✅ Request without consultation → 400
- ✅ Request with payment PENDING → 403
- ✅ Request for CLOSED visit → 403
- ✅ Audit log created on all actions
- ✅ Role-based field visibility verified

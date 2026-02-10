# Radiology Request API Implementation Summary

## Backend API Structure

### Models (`models.py`)
- **RadiologyRequest**: Visit-scoped and consultation-dependent
  - ForeignKey to Visit (visit-scoped)
  - ForeignKey to Consultation (consultation-dependent, REQUIRED)
  - Fields: study_type, study_code, clinical_indication, instructions, status, report
  - Image metadata: image_count, image_metadata (JSON, no raw DICOM)
  - User tracking: ordered_by (Doctor), reported_by (Radiology Tech)
  - Validation: Ensures consultation belongs to visit, visit is not CLOSED

### Serializers (`serializers.py`)
- **RadiologyRequestCreateSerializer**: Doctor creates requests
  - Fields: study_type (required), study_code, clinical_indication, instructions
  - System sets: visit_id, consultation_id, ordered_by
  
- **RadiologyRequestReportSerializer**: Radiology Tech posts reports
  - Can update: report (required), status (COMPLETED/IN_PROGRESS), image_count, image_metadata
  - Read-only: study_type, study_code, clinical_indication, instructions, consultation_id
  - Data minimization: No consultation details visible
  
- **RadiologyRequestReadSerializer**: Role-based field visibility
  - Doctor: All fields
  - Radiology Tech: Limited fields (no consultation context)

### Views (`views.py`)
- **RadiologyRequestViewSet**: Visit-scoped ViewSet
  - Endpoint: `/api/v1/visits/{visit_id}/radiology/`
  - Actions:
    - `list()`: List radiology requests (role-based fields)
    - `retrieve()`: Get radiology request (role-based fields)
    - `create()`: Create radiology request (Doctor only)
    - `update()`/`partial_update()`: Update report (Radiology Tech only)
    - `destroy()`: DISABLED (compliance)

### Permissions (`permissions.py`)
- **IsDoctorOrRadiologyTech**: Base permission (both roles allowed)
- **CanCreateRadiologyRequest**: Doctor only (create)
- **CanUpdateRadiologyReport**: Radiology Tech only (update reports)
- **CanViewRadiologyRequest**: Both roles (view with different fields)

### URL Configuration (`urls.py`)
- Router-based URL configuration
- Nested under `/api/v1/visits/{visit_id}/radiology/`
- Integrated into `apps/visits/urls.py`

## Role Enforcement Logic

### Doctor Permissions
```python
# Can do:
✅ POST /api/v1/visits/{visit_id}/radiology/        # Create requests
✅ GET  /api/v1/visits/{visit_id}/radiology/        # View all requests
✅ GET  /api/v1/visits/{visit_id}/radiology/{id}/   # View request details

# Cannot do:
❌ PATCH /api/v1/visits/{visit_id}/radiology/{id}/   # Update reports
❌ DELETE /api/v1/visits/{visit_id}/radiology/{id}/ # Delete requests
```

### Radiology Tech Permissions
```python
# Can do:
✅ GET   /api/v1/visits/{visit_id}/radiology/        # View requests (limited fields)
✅ GET   /api/v1/visits/{visit_id}/radiology/{id}/   # View request details (limited)
✅ PATCH /api/v1/visits/{visit_id}/radiology/{id}/   # Update reports

# Cannot do:
❌ POST   /api/v1/visits/{visit_id}/radiology/        # Create requests
❌ DELETE /api/v1/visits/{visit_id}/radiology/{id}/   # Delete requests
```

## Data Visibility Rules

### Doctor Sees (Full Access)
```json
{
  "id": 1,
  "visit_id": 123,
  "consultation_id": 45,                    // ✅ Visible
  "study_type": "Chest X-Ray",
  "study_code": "CXR",
  "clinical_indication": "Suspected pneumonia",
  "instructions": "PA and lateral views",
  "status": "COMPLETED",
  "report": "No acute cardiopulmonary...",  // ✅ Visible
  "report_date": "2024-01-15...",
  "image_count": 2,
  "image_metadata": {...},                   // ✅ Visible
  "ordered_by": 10,
  "reported_by": 16,
  "created_at": "...",
  "updated_at": "..."
}
```

### Radiology Tech Sees (Limited Access)
```json
{
  "id": 1,
  "visit_id": 123,
  "consultation_id": 45,                    // ⚠️ Visible but no details
  "study_type": "Chest X-Ray",              // ✅ Read-only
  "study_code": "CXR",                       // ✅ Read-only
  "clinical_indication": "Suspected...",     // ✅ Read-only
  "instructions": "PA and lateral views",     // ✅ Read-only
  "status": "COMPLETED",
  "report": "No acute cardiopulmonary...",  // ✅ Can update
  "report_date": "2024-01-15...",
  "image_count": 2,                          // ✅ Can update
  "image_metadata": {...},                   // ✅ Can update
  "ordered_by": 10,                          // ✅ Read-only
  "reported_by": 16,
  "created_at": "...",
  "updated_at": "..."
}
```

**Radiology Tech Cannot See:**
- Consultation details (history, examination, diagnosis)
- Patient information beyond what's in visit
- Diagnosis or clinical notes

## Enforcement Points

### 1. Consultation Dependency
```python
def get_consultation(self, visit):
    consultation = Consultation.objects.filter(visit=visit).first()
    if not consultation:
        raise DRFValidationError(
            "Consultation must exist before creating radiology requests."
        )
    return consultation
```

### 2. Role Enforcement
```python
# Create: Doctor only
if user_role != 'DOCTOR':
    raise PermissionDenied("Only doctors can create radiology requests.")

# Update: Radiology Tech only
if user_role == 'RADIOLOGY_TECH':
    # Can update reports
elif user_role == 'DOCTOR':
    raise PermissionDenied("Doctors cannot update radiology requests.")
```

### 3. Payment Enforcement
```python
def check_payment_status(self, visit):
    if not visit.is_payment_cleared():
        raise PermissionDenied(
            "Payment must be cleared before creating radiology requests."
        )
```

### 4. Visit Status Enforcement
```python
def check_visit_status(self, visit):
    if visit.status == 'CLOSED':
        raise PermissionDenied(
            "Cannot create or modify radiology requests for a CLOSED visit."
        )
```

### 5. Audit Logging
```python
log_radiology_request_action(
    user=request.user,
    action='create',  # or 'update_report', 'read'
    visit_id=visit.id,
    radiology_request_id=radiology_request.id,
    request=request
)
```

## Image Metadata Structure

Image metadata is stored as JSON (no raw DICOM):

```json
{
  "modality": "CT",
  "series": ["Axial", "Coronal", "Sagittal"],
  "slices": 120,
  "slice_thickness": "1mm",
  "kvp": 120,
  "ma": 200
}
```

**Note**: Raw DICOM files are not stored. Only metadata is captured.

## Rejected Patterns

❌ **Standalone Radiology Endpoints:**
- `/api/radiology/` → REJECTED
- `/api/imaging/` → REJECTED
- Any endpoint without `{visit_id}` → REJECTED

❌ **Radiology Requests Without Consultation:**
- Creating request without consultation → REJECTED
- Request without consultation_id → REJECTED

❌ **Role Overlap:**
- Doctor updating reports → REJECTED
- Radiology Tech creating requests → REJECTED

❌ **Bypassing Payment:**
- Creating request with payment PENDING → REJECTED
- Middleware bypass → REJECTED

## Compliance Checklist

✅ **Visit-Scoped**: All endpoints nested under `/visits/{visit_id}/`  
✅ **Consultation-Dependent**: Radiology requests require consultation  
✅ **Doctor-Only Creation**: Only doctors can create requests  
✅ **Radiology Tech-Only Reports**: Only Radiology Tech can post reports  
✅ **Payment Enforcement**: Payment must be CLEARED  
✅ **Visit Status**: Visit must be OPEN for mutations  
✅ **Audit Logging**: All actions logged  
✅ **Data Minimization**: Radiology Tech sees limited fields  
✅ **No Standalone Flow**: Radiology requests cannot exist without consultation  
✅ **Image Metadata Only**: No raw DICOM stored  

## Testing Requirements

The implementation must pass:
- ✅ Radiology Tech cannot create requests → 403
- ✅ Doctor cannot update reports → 403
- ✅ Request without consultation → 400
- ✅ Request with payment PENDING → 403
- ✅ Request for CLOSED visit → 403
- ✅ Audit log created on all actions
- ✅ Role-based field visibility verified

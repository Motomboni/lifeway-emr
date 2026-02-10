# Prescription API Implementation Summary

## Backend API Structure

### Models (`models.py`)
- **Prescription**: Visit-scoped and consultation-dependent
  - ForeignKey to Visit (visit-scoped)
  - ForeignKey to Consultation (consultation-dependent, REQUIRED)
  - Fields: drug, drug_code, dosage, frequency, duration, quantity, instructions
  - Status tracking: PENDING, DISPENSED, CANCELLED
  - Dispensing: dispensed, dispensed_date, dispensing_notes
  - User tracking: prescribed_by (Doctor), dispensed_by (Pharmacist)
  - Validation: Ensures consultation belongs to visit, visit is not CLOSED

### Serializers (`serializers.py`)
- **PrescriptionCreateSerializer**: Doctor creates prescriptions
  - Fields: drug (required), drug_code, dosage (required), frequency, duration, quantity, instructions
  - System sets: visit_id, consultation_id, prescribed_by
  
- **PrescriptionReadSerializer**: Role-based field visibility
  - Doctor: All fields
  - Pharmacist: Limited fields (no consultation context)

### Views (`views.py`)
- **PrescriptionViewSet**: Visit-scoped ViewSet
  - Endpoint: `/api/v1/visits/{visit_id}/prescriptions/`
  - Actions:
    - `list()`: List prescriptions (role-based fields)
    - `retrieve()`: Get prescription (role-based fields)
    - `create()`: Create prescription (Doctor only)
    - `update()`/`partial_update()`: Dispense prescription (Pharmacist only)
    - `destroy()`: DISABLED (compliance)

### Permissions (`permissions.py`)
- **IsDoctor**: Doctor only (create)
- **CanDispensePrescription**: Pharmacist only (update/dispense)
- **CanViewPrescription**: Both roles (view with different fields)

### URL Configuration (`urls.py`)
- Router-based URL configuration
- Nested under `/api/v1/visits/{visit_id}/prescriptions/`
- Integrated into `apps/visits/urls.py`

## Role Enforcement Logic

### Doctor Permissions
```python
# Can do:
✅ POST /api/v1/visits/{visit_id}/prescriptions/        # Create prescriptions
✅ GET  /api/v1/visits/{visit_id}/prescriptions/        # View all prescriptions
✅ GET  /api/v1/visits/{visit_id}/prescriptions/{id}/   # View prescription details

# Cannot do:
❌ PATCH /api/v1/visits/{visit_id}/prescriptions/{id}/   # Dispense (only Pharmacist)
❌ DELETE /api/v1/visits/{visit_id}/prescriptions/{id}/ # Delete prescriptions
```

### Pharmacist Permissions
```python
# Can do:
✅ GET   /api/v1/visits/{visit_id}/prescriptions/        # View prescriptions (limited fields)
✅ GET   /api/v1/visits/{visit_id}/prescriptions/{id}/   # View prescription details (limited)
✅ PATCH /api/v1/visits/{visit_id}/prescriptions/{id}/   # Dispense medication

# Cannot do:
❌ POST   /api/v1/visits/{visit_id}/prescriptions/        # Create prescriptions
❌ DELETE /api/v1/visits/{visit_id}/prescriptions/{id}/   # Delete prescriptions
```

## Data Visibility Rules

### Doctor Sees (Full Access)
```json
{
  "id": 1,
  "visit_id": 123,
  "consultation_id": 45,                    // ✅ Visible
  "drug": "Amoxicillin",
  "drug_code": "AMX-500",
  "dosage": "500mg",
  "frequency": "TID",
  "duration": "7 days",
  "quantity": "21 tablets",
  "instructions": "Take with food",
  "status": "DISPENSED",
  "dispensed": true,                         // ✅ Visible
  "dispensed_date": "2024-01-15...",         // ✅ Visible
  "dispensing_notes": "...",                 // ✅ Visible
  "prescribed_by": 10,
  "dispensed_by": 17,
  "created_at": "...",
  "updated_at": "..."
}
```

### Pharmacist Sees (Limited Access)
```json
{
  "id": 1,
  "visit_id": 123,
  "consultation_id": 45,                    // ⚠️ Visible but no details
  "drug": "Amoxicillin",                    // ✅ Read-only
  "drug_code": "AMX-500",                   // ✅ Read-only
  "dosage": "500mg",                        // ✅ Read-only
  "frequency": "TID",                       // ✅ Read-only
  "duration": "7 days",                     // ✅ Read-only
  "quantity": "21 tablets",                 // ✅ Read-only
  "instructions": "Take with food",         // ✅ Read-only
  "status": "DISPENSED",
  "dispensed": true,                         // ✅ Can update
  "dispensed_date": "2024-01-15...",
  "dispensing_notes": "...",                 // ✅ Can update
  "prescribed_by": 10,                      // ✅ Read-only
  "dispensed_by": 17,
  "created_at": "...",
  "updated_at": "..."
}
```

**Pharmacist Cannot See:**
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
            "Consultation must exist before creating prescriptions."
        )
    return consultation
```

### 2. Role Enforcement
```python
# Create: Doctor only
if user_role != 'DOCTOR':
    raise PermissionDenied("Only doctors can create prescriptions.")

# Update: Pharmacist only
if user_role == 'PHARMACIST':
    # Can dispense
elif user_role == 'DOCTOR':
    raise PermissionDenied("Doctors cannot update prescriptions.")
```

### 3. Payment Enforcement
```python
def check_payment_status(self, visit):
    if not visit.is_payment_cleared():
        raise PermissionDenied(
            "Payment must be cleared before creating prescriptions."
        )
```

### 4. Visit Status Enforcement
```python
def check_visit_status(self, visit):
    if visit.status == 'CLOSED':
        raise PermissionDenied(
            "Cannot create or modify prescriptions for a CLOSED visit."
        )
```

### 5. Audit Logging
```python
log_prescription_action(
    user=request.user,
    action='create',  # or 'dispense', 'read'
    visit_id=visit.id,
    prescription_id=prescription.id,
    request=request
)
```

## Rejected Patterns

❌ **Standalone Prescription Endpoints:**
- `/api/prescriptions/` → REJECTED
- `/api/pharmacy/` → REJECTED
- Any endpoint without `{visit_id}` → REJECTED

❌ **Prescriptions Without Consultation:**
- Creating prescription without consultation → REJECTED
- Prescription without consultation_id → REJECTED

❌ **Role Overlap:**
- Doctor dispensing medication → REJECTED
- Pharmacist creating prescriptions → REJECTED

❌ **Bypassing Payment:**
- Creating prescription with payment PENDING → REJECTED
- Middleware bypass → REJECTED

## Compliance Checklist

✅ **Visit-Scoped**: All endpoints nested under `/visits/{visit_id}/`  
✅ **Consultation-Dependent**: Prescriptions require consultation  
✅ **Doctor-Only Creation**: Only doctors can create prescriptions  
✅ **Payment Enforcement**: Payment must be CLEARED  
✅ **Visit Status**: Visit must be OPEN for mutations  
✅ **Audit Logging**: All actions logged  
✅ **Data Minimization**: Pharmacist sees limited fields  
✅ **No Standalone Flow**: Prescriptions cannot exist without consultation  

## Testing Requirements

The implementation must pass:
- ✅ Pharmacist cannot create prescriptions → 403
- ✅ Doctor cannot dispense → 403
- ✅ Prescription without consultation → 400
- ✅ Prescription with payment PENDING → 403
- ✅ Prescription for CLOSED visit → 403
- ✅ Audit log created on all actions
- ✅ Role-based field visibility verified

# Lab Order API Implementation Summary

## Backend API Structure

### Models (`models.py`)
- **LabOrder**: Visit-scoped and consultation-dependent
  - ForeignKey to Visit (visit-scoped)
  - ForeignKey to Consultation (consultation-dependent, REQUIRED)
  - Fields: test_name, test_code, instructions, status, result
  - User tracking: ordered_by (Doctor), resulted_by (Lab Tech)
  - Validation: Ensures consultation belongs to visit, visit is not CLOSED

### Serializers (`serializers.py`)
- **LabOrderCreateSerializer**: Doctor creates orders
  - Fields: test_name (required), test_code, instructions
  - System sets: visit_id, consultation_id, ordered_by
  
- **LabOrderResultSerializer**: Lab Tech posts results
  - Can update: result (required), status (COMPLETED/IN_PROGRESS)
  - Read-only: test_name, test_code, instructions, consultation_id
  - Data minimization: No consultation details visible
  
- **LabOrderReadSerializer**: Role-based field visibility
  - Doctor: All fields
  - Lab Tech: Limited fields (no consultation context)

### Views (`views.py`)
- **LabOrderViewSet**: Visit-scoped ViewSet
  - Endpoint: `/api/v1/visits/{visit_id}/laboratory/`
  - Actions:
    - `list()`: List lab orders (role-based fields)
    - `retrieve()`: Get lab order (role-based fields)
    - `create()`: Create lab order (Doctor only)
    - `update()`/`partial_update()`: Update result (Lab Tech only)
    - `destroy()`: DISABLED (compliance)

### Permissions (`permissions.py`)
- **IsDoctorOrLabTech**: Base permission (both roles allowed)
- **CanCreateLabOrder**: Doctor only (create)
- **CanUpdateLabResult**: Lab Tech only (update results)
- **CanViewLabOrder**: Both roles (view with different fields)

### URL Configuration (`urls.py`)
- Router-based URL configuration
- Nested under `/api/v1/visits/{visit_id}/laboratory/`
- Integrated into `apps/visits/urls.py`

## Role Enforcement Logic

### Doctor Permissions
```python
# Can do:
✅ POST /api/v1/visits/{visit_id}/laboratory/        # Create orders
✅ GET  /api/v1/visits/{visit_id}/laboratory/        # View all orders
✅ GET  /api/v1/visits/{visit_id}/laboratory/{id}/   # View order details

# Cannot do:
❌ PATCH /api/v1/visits/{visit_id}/laboratory/{id}/   # Update results
❌ DELETE /api/v1/visits/{visit_id}/laboratory/{id}/ # Delete orders
```

### Lab Tech Permissions
```python
# Can do:
✅ GET   /api/v1/visits/{visit_id}/laboratory/        # View orders (limited fields)
✅ GET   /api/v1/visits/{visit_id}/laboratory/{id}/   # View order details (limited)
✅ PATCH /api/v1/visits/{visit_id}/laboratory/{id}/   # Update results

# Cannot do:
❌ POST   /api/v1/visits/{visit_id}/laboratory/        # Create orders
❌ DELETE /api/v1/visits/{visit_id}/laboratory/{id}/   # Delete orders
```

## Data Visibility Rules

### Doctor Sees (Full Access)
```json
{
  "id": 1,
  "visit_id": 123,
  "consultation_id": 45,           // ✅ Visible
  "test_name": "CBC",
  "test_code": "CBC001",
  "instructions": "Fasting",
  "status": "COMPLETED",
  "result": "WBC: 7.2...",        // ✅ Visible
  "result_date": "2024-01-15...",
  "ordered_by": 10,
  "resulted_by": 15,
  "created_at": "...",
  "updated_at": "..."
}
```

### Lab Tech Sees (Limited Access)
```json
{
  "id": 1,
  "visit_id": 123,
  "consultation_id": 45,           // ⚠️ Visible but no details
  "test_name": "CBC",              // ✅ Read-only
  "test_code": "CBC001",            // ✅ Read-only
  "instructions": "Fasting",        // ✅ Read-only
  "status": "COMPLETED",
  "result": "WBC: 7.2...",         // ✅ Can update
  "result_date": "2024-01-15...",
  "ordered_by": 10,                 // ✅ Read-only
  "resulted_by": 15,
  "created_at": "...",
  "updated_at": "..."
}
```

**Lab Tech Cannot See:**
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
            "Consultation must exist before creating lab orders."
        )
    return consultation
```

### 2. Role Enforcement
```python
# Create: Doctor only
if user_role != 'DOCTOR':
    raise PermissionDenied("Only doctors can create lab orders.")

# Update: Lab Tech only
if user_role == 'LAB_TECH':
    # Can update results
elif user_role == 'DOCTOR':
    raise PermissionDenied("Doctors cannot update lab orders.")
```

### 3. Payment Enforcement
```python
def check_payment_status(self, visit):
    if not visit.is_payment_cleared():
        raise PermissionDenied(
            "Payment must be cleared before creating lab orders."
        )
```

### 4. Visit Status Enforcement
```python
def check_visit_status(self, visit):
    if visit.status == 'CLOSED':
        raise PermissionDenied(
            "Cannot create or modify lab orders for a CLOSED visit."
        )
```

### 5. Audit Logging
```python
log_lab_order_action(
    user=request.user,
    action='create',  # or 'update_result', 'read'
    visit_id=visit.id,
    lab_order_id=lab_order.id,
    request=request
)
```

## Rejected Patterns

❌ **Standalone Lab Endpoints:**
- `/api/lab/` → REJECTED
- `/api/laboratory/` → REJECTED
- Any endpoint without `{visit_id}` → REJECTED

❌ **Lab Orders Without Consultation:**
- Creating lab order without consultation → REJECTED
- Lab order without consultation_id → REJECTED

❌ **Role Overlap:**
- Doctor updating results → REJECTED
- Lab Tech creating orders → REJECTED

❌ **Bypassing Payment:**
- Creating lab order with payment PENDING → REJECTED
- Middleware bypass → REJECTED

## Compliance Checklist

✅ **Visit-Scoped**: All endpoints nested under `/visits/{visit_id}/`  
✅ **Consultation-Dependent**: Lab orders require consultation  
✅ **Doctor-Only Creation**: Only doctors can create orders  
✅ **Lab Tech-Only Results**: Only Lab Tech can post results  
✅ **Payment Enforcement**: Payment must be CLEARED  
✅ **Visit Status**: Visit must be OPEN  
✅ **Audit Logging**: All actions logged  
✅ **Data Minimization**: Lab Tech sees limited fields  
✅ **No Standalone Flow**: Lab orders cannot exist without consultation  

## Testing Requirements

The implementation must pass:
- ✅ Lab Tech cannot create lab orders → 403
- ✅ Doctor cannot update results → 403
- ✅ Lab order without consultation → 400
- ✅ Lab order with payment PENDING → 403
- ✅ Lab order for CLOSED visit → 403
- ✅ Audit log created on all actions
- ✅ Role-based field visibility verified

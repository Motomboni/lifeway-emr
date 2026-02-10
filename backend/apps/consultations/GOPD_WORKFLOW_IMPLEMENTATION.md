# GOPD Consultation Workflow Implementation

## Overview

This document describes the implementation of the GOPD Consultation workflow that is driven entirely by ServiceCatalog. The workflow ensures proper payment enforcement, doctor assignment, and consultation lifecycle management.

## Architecture

### Service-Driven Design

The workflow is orchestrated by the `gopd_workflow_service.py` module, which:
- Creates/gets Visit when a GOPD_CONSULT service is selected
- Creates Consultation based on payment timing configuration
- Enforces payment guards before doctor access
- Supports auto-assignment of doctors from ServiceCatalog

### Key Components

1. **ServiceCatalog Model** (`backend/apps/billing/service_catalog_models.py`)
   - Added `auto_assign_doctor` field for automatic doctor assignment
   - `workflow_type = 'GOPD_CONSULT'` triggers the workflow
   - `bill_timing` determines when payment is required (BEFORE or AFTER)

2. **Consultation Model** (`backend/apps/consultations/models.py`)
   - Added `status` field: PENDING → ACTIVE → CLOSED
   - `created_by` is now nullable (can be auto-assigned later)
   - Status validation in `clean()` method

3. **GOPD Workflow Service** (`backend/apps/consultations/gopd_workflow_service.py`)
   - `initiate_gopd_consultation_workflow()`: Main orchestration function
   - `create_consultation_after_payment()`: Creates consultation when payment is confirmed
   - `can_doctor_access_consultation()`: Checks doctor access permissions
   - `activate_consultation()`: Activates PENDING consultation
   - `close_consultation()`: Closes ACTIVE consultation

4. **Permissions** (`backend/core/permissions.py`)
   - `IsGOPDConsultationAccessible`: Enforces payment and status-based access
   - Works with existing `IsPaymentCleared` and `IsVisitOpen` permissions

## Workflow Rules

### When Service is Selected

1. **Service Validation**
   - Must have `workflow_type = 'GOPD_CONSULT'`
   - Must be `is_active = True`

2. **Visit Creation**
   - If no active visit exists, create one
   - Visit type is set to 'CONSULTATION'
   - Visit status is 'OPEN'
   - Payment status is 'UNPAID' initially

3. **Consultation Creation**
   - **If `bill_timing = 'BEFORE'`**:
     - Consultation is NOT created until payment is cleared
     - Doctor access is locked until payment is confirmed
   - **If `bill_timing = 'AFTER'`**:
     - Consultation is created immediately with status 'ACTIVE'
     - Payment can be processed after consultation

4. **Doctor Assignment**
   - If `auto_assign_doctor` is set in ServiceCatalog, doctor is auto-assigned
   - Otherwise, `created_by` is None (unassigned)
   - Unassigned consultations can be accessed by any doctor

### Consultation Status Flow

```
PENDING → ACTIVE → CLOSED
```

- **PENDING**: Awaiting payment or doctor assignment
  - Created when `bill_timing = 'BEFORE'` and payment not cleared
  - Can be activated when payment is cleared
  
- **ACTIVE**: Consultation in progress
  - Doctor can document clinical findings
  - Only assigned doctor can access (if assigned)
  
- **CLOSED**: Consultation completed
  - Read-only access
  - Cannot be modified

### Payment Guards

1. **Before Consultation Creation** (if `bill_timing = 'BEFORE'`)
   - Payment must be cleared before consultation is created
   - Doctor access is locked until payment is confirmed

2. **Before Consultation Activation** (if status is PENDING)
   - Payment must be cleared before PENDING consultation can be activated
   - `activate_consultation()` enforces this check

3. **Permission Enforcement**
   - `IsGOPDConsultationAccessible` checks payment status
   - `IsPaymentCleared` is used in consultation views
   - Both work together to enforce payment guards

## Usage Examples

### Initiating GOPD Consultation Workflow

```python
from apps.consultations.gopd_workflow_service import initiate_gopd_consultation_workflow
from apps.billing.service_catalog_models import ServiceCatalog
from apps.patients.models import Patient

# Get service
service = ServiceCatalog.objects.get(workflow_type='GOPD_CONSULT', is_active=True)

# Initiate workflow
visit, consultation, created = initiate_gopd_consultation_workflow(
    patient=patient,
    service=service,
    user=request.user,
    payment_type='CASH',
    chief_complaint='Headache',
)

if consultation:
    print(f"Consultation created: {consultation.id}, Status: {consultation.status}")
else:
    print("Consultation pending payment")
```

### Creating Consultation After Payment

```python
from apps.consultations.gopd_workflow_service import create_consultation_after_payment

# When payment is confirmed
consultation = create_consultation_after_payment(
    visit=visit,
    service=service,
    assigned_doctor=doctor,  # Optional
)
```

### Checking Doctor Access

```python
from apps.consultations.gopd_workflow_service import can_doctor_access_consultation

if can_doctor_access_consultation(consultation, doctor):
    # Doctor can access consultation
    pass
else:
    # Access denied
    pass
```

### Activating PENDING Consultation

```python
from apps.consultations.gopd_workflow_service import activate_consultation

# After payment is cleared
consultation = activate_consultation(consultation, doctor)
```

## Database Migrations

Two migrations were created:

1. **Consultation Model** (`0004_consultation_status_alter_consultation_created_by_and_more.py`)
   - Adds `status` field
   - Makes `created_by` nullable
   - Adds index on `status`

2. **ServiceCatalog Model** (`0013_servicecatalog_auto_assign_doctor.py`)
   - Adds `auto_assign_doctor` ForeignKey field

## Integration Points

### API Views

The workflow service should be integrated into:
- Service selection endpoint (when GOPD_CONSULT service is selected)
- Payment confirmation endpoint (to create consultation after payment)
- Consultation views (to enforce access controls)

### Payment Processing

When payment is processed:
1. Check if visit has a PENDING consultation
2. If yes, call `create_consultation_after_payment()`
3. Or call `activate_consultation()` if consultation exists but is PENDING

## Testing

Unit tests should cover:
- Visit creation for GOPD_CONSULT service
- Consultation creation with different bill_timing values
- Payment guard enforcement
- Doctor assignment (auto and manual)
- Status transitions (PENDING → ACTIVE → CLOSED)
- Access control checks

## Future Enhancements

- Support for multiple consultations per visit (if needed)
- Queue management for unassigned consultations
- Notification system for pending consultations
- Analytics on consultation workflow metrics


# Downstream Service Workflow - Service-Driven Architecture

## Overview

This document describes the service-driven workflow for downstream services (LAB, PHARMACY, PROCEDURES, RADIOLOGY) in the EMR system. When a service is selected from the ServiceCatalog, the system automatically creates the appropriate domain object and billing.

## Architecture

### Service-Driven Design

The system uses `ServiceCatalog` to drive workflows:
- Selecting a service automatically creates domain objects
- Billing is auto-generated
- Role-based access is enforced
- Visit-scoped and consultation-dependent rules are strictly respected

### Components

1. **Downstream Service Workflow** (`downstream_service_workflow.py`)
   - `order_downstream_service()`: Main orchestrator
   - `_order_lab_service()`: LAB service handler
   - `_order_pharmacy_service()`: PHARMACY service handler
   - `_order_procedure_service()`: PROCEDURE service handler
   - `can_dispense_prescription()`: Prescription dispensing check

2. **Domain Models**
   - `LabOrder`: Laboratory orders
   - `Prescription`: Pharmacy prescriptions
   - `ProcedureTask`: Nurse-executed procedures
   - `RadiologyRequest`: Radiology studies

3. **Billing Integration**
   - Auto-generates `BillingLineItem` for all services
   - Links to consultation for consultation-dependent services

## Service Rules

### LAB Services

**Requirements:**
- `require_visit = true`
- `require_consultation = true`
- `workflow_type = 'LAB_ORDER'`
- Ordered ONLY by doctors (`allowed_roles = ['DOCTOR']`)

**Workflow:**
1. Doctor selects LAB service from ServiceCatalog
2. System validates: visit OPEN, consultation ACTIVE/CLOSED, user is DOCTOR
3. System creates `LabOrder` with tests_requested
4. System auto-generates `BillingLineItem`
5. Returns `(LabOrder, BillingLineItem)`

**Additional Data Required:**
```python
{
    'tests_requested': ['CBC', 'Hemoglobin', 'Platelet Count'],  # Required
    'clinical_indication': 'Routine checkup',  # Optional
}
```

### PHARMACY Services

**Requirements:**
- `require_consultation = true`
- `workflow_type = 'DRUG_DISPENSE'`
- Dispensed ONLY after billing is paid

**Workflow:**
1. Doctor selects PHARMACY service from ServiceCatalog
2. System validates: visit OPEN, consultation ACTIVE/CLOSED
3. System creates `Prescription` with drug details
4. System auto-generates `BillingLineItem`
5. Returns `(Prescription, BillingLineItem)`
6. Prescription can only be dispensed after billing is PAID

**Additional Data Required:**
```python
{
    'drug': 'Paracetamol',  # Required (drug name)
    'drug_code': 'PARA-001',  # Optional
    'dosage': '500mg',  # Required
    'frequency': 'BID',  # Optional
    'duration': '7 days',  # Optional
    'instructions': 'Take with food',  # Optional
    'quantity': '14 tablets',  # Optional
}
```

### PROCEDURES Services

**Requirements:**
- `require_consultation = true`
- `workflow_type = 'PROCEDURE'`
- Nurse-executed
- Consultation-dependent

**Workflow:**
1. Doctor/Nurse selects PROCEDURE service from ServiceCatalog
2. System validates: visit OPEN, consultation ACTIVE/CLOSED
3. System creates `ProcedureTask` with procedure details
4. System auto-generates `BillingLineItem`
5. Returns `(ProcedureTask, BillingLineItem)`
6. Nurse executes procedure (updates status to COMPLETED)

**Additional Data Required:**
```python
{
    'clinical_indication': 'Wound care',  # Optional
}
```

## Usage Examples

### Ordering LAB Service

```python
from apps.visits.downstream_service_workflow import order_downstream_service

# Order LAB service
lab_order, billing_line_item = order_downstream_service(
    service=lab_service,  # ServiceCatalog with workflow_type='LAB_ORDER'
    visit=visit,
    consultation=consultation,
    user=doctor,
    additional_data={
        'tests_requested': ['CBC', 'Hemoglobin'],
        'clinical_indication': 'Routine checkup',
    },
)
```

### Ordering PHARMACY Service

```python
# Order PHARMACY service
prescription, billing_line_item = order_downstream_service(
    service=pharmacy_service,  # ServiceCatalog with workflow_type='DRUG_DISPENSE'
    visit=visit,
    consultation=consultation,
    user=doctor,
    additional_data={
        'drug': 'Paracetamol',
        'dosage': '500mg',
        'frequency': 'BID',
        'duration': '7 days',
    },
)
```

### Ordering PROCEDURE Service

```python
# Order PROCEDURE service
procedure_task, billing_line_item = order_downstream_service(
    service=procedure_service,  # ServiceCatalog with workflow_type='PROCEDURE'
    visit=visit,
    consultation=consultation,
    user=doctor,
    additional_data={
        'clinical_indication': 'Wound care',
    },
)
```

### Ordering RADIOLOGY Service

```python
# Order RADIOLOGY service
radiology_request, billing_line_item = order_downstream_service(
    service=radiology_service,  # ServiceCatalog with workflow_type='RADIOLOGY_STUDY'
    visit=visit,
    consultation=consultation,
    user=doctor,
    additional_data={
        'study_type': 'Chest X-Ray',
        'clinical_indication': 'Suspected pneumonia',
        'instructions': 'PA and lateral views',
    },
)
```

### Checking Prescription Dispensing

```python
from apps.visits.downstream_service_workflow import can_dispense_prescription

# Check if prescription can be dispensed
if can_dispense_prescription(prescription):
    # Dispense prescription
    prescription.status = 'DISPENSED'
    prescription.save()
```

## Validation Rules

### Visit Validation
- Visit must be OPEN (not CLOSED)
- Visit payment must be cleared (for LAB and PHARMACY services)

### Consultation Validation
- Consultation must exist (for consultation-dependent services)
- Consultation must belong to the visit
- Consultation must be ACTIVE or CLOSED (not PENDING)

### Role Validation
- LAB services: Only DOCTOR can order
- PHARMACY services: Typically DOCTOR (configurable via `allowed_roles`)
- PROCEDURES: DOCTOR or NURSE (configurable via `allowed_roles`)
- RADIOLOGY services: Only DOCTOR can order

### Service Validation
- Service must be active (`is_active = True`)
- Service must have correct `workflow_type`
- Service must have correct `requires_visit` and `requires_consultation` flags

## Billing Integration

### Auto-Generation

All downstream services automatically generate `BillingLineItem`:
- Amount is snapshotted from `ServiceCatalog`
- Links to `visit` and `consultation` (if consultation-dependent)
- `bill_status` starts as `PENDING`
- Can be paid via `apply_payment()`

### Prescription Dispensing

Prescriptions can only be dispensed after billing is paid:
- `can_dispense_prescription()` checks if billing is PAID
- System enforces: `prescription.status = 'PENDING'` and `billing_line_item.bill_status = 'PAID'`

## Error Handling

### Validation Errors

The workflow raises `ValidationError` for:
- Invalid service configuration
- Missing required data
- Role violations
- Visit/consultation state violations
- Payment clearance violations

### Transaction Safety

All operations use `transaction.atomic()` to ensure:
- Domain object and billing are created together
- Rollback on any error
- Database consistency

## Testing

### Test Coverage

The test suite (`tests_downstream_services.py`) covers:
- LAB service ordering (creates LabOrder and billing)
- PHARMACY service ordering (creates Prescription and billing)
- PROCEDURE service ordering (creates ProcedureTask and billing)
- Role-based access enforcement
- Visit-scoped validation
- Consultation-dependent validation
- Prescription dispensing rules

## Future Enhancements

- Batch ordering (multiple services at once)
- Service templates (pre-configured service combinations)
- Workflow state machine (explicit state transitions)
- Service scheduling (future-dated services)
- Service cancellation/refund workflow


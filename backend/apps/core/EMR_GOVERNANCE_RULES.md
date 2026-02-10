# EMR Governance Rules - Nigerian Clinic Operational Realities

## Overview

This document describes the strict governance rules enforced across the EMR system to ensure clinical workflow integrity and align with Nigerian clinic operational realities.

## Core Governance Rules

### 1. No LabOrder without Consultation

**Rule:** All lab orders MUST have a consultation.

**Applies to:** `LabOrder`, `RadiologyRequest`

### 2. No Consultation without Visit

**Rule:** Consultations CANNOT exist without a visit.

**Applies to:** `Consultation`

### 3. No Result Posting without Active Order

**Rule:** Lab results and Radiology reports can ONLY be posted for active orders/requests.

**Applies to:** `LabResult`, `RadiologyRequest` (report posting)

### 4. No Drug Dispensing without Paid Bill (Unless Emergency)

**Rule:** Prescriptions can ONLY be dispensed if billing is paid, unless flagged as emergency.

**Applies to:** `Prescription`

---

## Detailed Rules

### 1. No LabOrder without Consultation

**Rule:** All lab orders MUST have a consultation.

**Enforcement:**
- Database constraint: `consultation` field is `NOT NULL`
- Model validator: `validate_consultation_required`
- Model `clean()` method: Explicit validation with clear error messages

**Rationale (Nigerian Clinic Context):**
- Lab orders require clinical context from consultation
- Ensures proper documentation and billing traceability
- Prevents orphaned lab orders without clinical justification

**Error Message:**
```
"Lab orders require a consultation. Per Nigerian clinic operational rules, 
all lab orders must have clinical context from a consultation. 
Please ensure a consultation exists for this visit."
```

### 2. No Consultation without Visit

**Rule:** Consultations CANNOT exist without a visit.

**Enforcement:**
- Database constraint: `OneToOneField` with `null=False`
- Model validator: `validate_visit_required`
- Model `clean()` method: Explicit validation

**Rationale (Nigerian Clinic Context):**
- Visit is the single source of clinical truth
- Ensures proper patient context and billing integration
- Prevents consultations without visit context

**Error Message:**
```
"Consultations require a visit. Please create a visit first."
```

### 3. No Result Posting without Active Order

**Rule:** Lab results can ONLY be posted for active lab orders.

**Enforcement:**
- Database constraint: `lab_order` field is `NOT NULL` and `OneToOneField`
- Model validator: `validate_active_lab_order`
- Model `clean()` method: Validates order status is `ORDERED` or `SAMPLE_COLLECTED`

**Rationale (Nigerian Clinic Context):**
- Results must be linked to an active order
- Prevents posting results for cancelled or completed orders
- Ensures proper workflow: Order → Sample Collection → Result

**Error Message:**
```
"Lab results can only be posted for active lab orders. 
Current order status: '{status}'. Order ID: {order_id}. 
Please ensure the lab order is in ORDERED or SAMPLE_COLLECTED status before posting results."
```

### 4. No Radiology Report Posting without Active Request

**Rule:** Radiology reports can ONLY be posted for active radiology requests.

**Enforcement:**
- Database constraint: `report` field is linked to `RadiologyRequest`
- Model validator: `validate_active_radiology_request`
- Service function: `post_radiology_report()` validates request status

**Rationale (Nigerian Clinic Context):**
- Reports must be linked to an active request
- Prevents posting reports for cancelled or completed requests
- Ensures proper workflow: Request → Study → Report

**Error Message:**
```
"Radiology reports can only be posted for active radiology requests. 
Current request status: '{status}'. Request ID: {request_id}. 
Please ensure the radiology request is in PENDING or IN_PROGRESS status before posting reports."
```

### 5. No Drug Dispensing without Paid Bill (Unless Emergency)

**Rule:** Prescriptions can ONLY be dispensed if billing is paid, unless flagged as emergency.

**Enforcement:**
- Model field: `is_emergency` (Boolean) for emergency override
- Model validator: `validate_prescription_dispensing`
- Service function: `dispense_prescription()` with emergency override support
- Model `clean()` method: Validates payment clearance (unless emergency)

**Rationale (Nigerian Clinic Context):**
- Standard flow: Payment must be cleared before dispensing
- Emergency override: Life-threatening situations require immediate medication
- Audit trail: Emergency dispensing is tracked and requires authorization

**Error Messages:**

**Standard (Payment Required):**
```
"Prescription cannot be dispensed until billing is paid. 
Current billing status: {status}. Outstanding amount: ₦{amount}. 
Please process payment before dispensing. 
For emergency cases, use the emergency override flag."
```

**Emergency Override:**
- Emergency flag allows dispensing without payment
- Requires proper authorization (pharmacist role)
- Audit trail records emergency dispensing

## Implementation Details

### Custom Validators

Located in `apps/core/validators.py`:

1. **`validate_consultation_required(value)`**
   - Validates consultation is not None
   - Used on `LabOrder.consultation` and `RadiologyRequest.consultation` fields

2. **`validate_visit_required(value)`**
   - Validates visit is not None
   - Used on `Consultation.visit` field

3. **`validate_active_lab_order(value)`**
   - Validates lab order exists and is active
   - Checks status is `ORDERED` or `SAMPLE_COLLECTED`
   - Used on `LabResult.lab_order` field

4. **`validate_active_radiology_request(value)`**
   - Validates radiology request exists and is active
   - Checks status is `PENDING` or `IN_PROGRESS`
   - Used in `post_radiology_report()` service function

5. **`validate_prescription_dispensing(value, emergency_override=False)`**
   - Validates billing is paid (unless emergency)
   - Checks prescription status is `PENDING`
   - Used in `dispense_prescription()` service function

### Database Constraints

**LabOrder:**
- `consultation` field: `null=False`, `blank=False`
- ForeignKey with `on_delete=models.PROTECT`

**Consultation:**
- `visit` field: `OneToOneField` with `null=False`, `blank=False`
- OneToOneField enforces one consultation per visit

**LabResult:**
- `lab_order` field: `OneToOneField` with `null=False`, `blank=False`
- OneToOneField enforces one result per order

**Prescription:**
- `consultation` field: `null=False`, `blank=False`
- `is_emergency` field: Boolean flag for emergency override
- ForeignKey with `on_delete=models.CASCADE`

### Model-Level Validation

All models implement `clean()` method with:
- Clear, actionable error messages
- Context-specific information (IDs, statuses, amounts)
- Nigerian clinic operational context in messages

### Service Functions

**`dispense_prescription()`** (`apps/pharmacy/prescription_service.py`):
- Validates pharmacist role
- Checks payment clearance (unless emergency)
- Updates prescription status to `DISPENSED`
- Records dispensing timestamp and pharmacist
- Supports emergency override flag

**`post_radiology_report()`** (`apps/radiology/radiology_service.py`):
- Validates radiology tech role
- Checks radiology request is active (PENDING or IN_PROGRESS)
- Updates request status to `COMPLETED`
- Records report text, timestamp, and radiology tech
- Records image metadata

## Usage Examples

### Creating LabOrder (Requires Consultation)

```python
# ✅ Valid: Consultation exists
lab_order = LabOrder.objects.create(
    visit=visit,
    consultation=consultation,  # REQUIRED
    ordered_by=doctor,
    tests_requested=['CBC', 'Hemoglobin'],
)

# ❌ Invalid: No consultation
lab_order = LabOrder.objects.create(
    visit=visit,
    consultation=None,  # Will raise ValidationError
    ordered_by=doctor,
    tests_requested=['CBC'],
)
```

### Creating Consultation (Requires Visit)

```python
# ✅ Valid: Visit exists
consultation = Consultation.objects.create(
    visit=visit,  # REQUIRED (OneToOneField)
    created_by=doctor,
    status='ACTIVE',
)

# ❌ Invalid: No visit (OneToOneField prevents this)
# This will fail at database level
```

### Posting Lab Result (Requires Active Order)

```python
# ✅ Valid: Active lab order
lab_result = LabResult.objects.create(
    lab_order=lab_order,  # Status must be ORDERED or SAMPLE_COLLECTED
    result_data='Normal values',
    recorded_by=lab_tech,
)

# ❌ Invalid: Inactive order
lab_order.status = 'RESULT_READY'
lab_order.save()
lab_result = LabResult.objects.create(
    lab_order=lab_order,  # Will raise ValidationError
    result_data='Normal values',
    recorded_by=lab_tech,
)
```

### Posting Radiology Report (Requires Active Request)

```python
from apps.radiology.radiology_service import post_radiology_report

# ✅ Valid: Active radiology request
radiology_request = post_radiology_report(
    radiology_request=radiology_request,  # Status must be PENDING or IN_PROGRESS
    radiology_tech=radiology_tech,
    report_text='Normal chest X-ray. No acute findings.',
    image_count=2,
)

# ❌ Invalid: Inactive request
radiology_request.status = 'COMPLETED'
radiology_request.save()

# Will raise ValidationError
radiology_request = post_radiology_report(
    radiology_request=radiology_request,  # Will raise ValidationError
    radiology_tech=radiology_tech,
    report_text='Normal findings',
)
```

### Dispensing Prescription (Requires Paid Bill)

```python
from apps.pharmacy.prescription_service import dispense_prescription

# ✅ Valid: Billing is paid
prescription = dispense_prescription(
    prescription=prescription,
    pharmacist=pharmacist,
    emergency_override=False,
    dispensing_notes='Dispensed as prescribed',
)

# ✅ Valid: Emergency override
prescription = dispense_prescription(
    prescription=prescription,
    pharmacist=pharmacist,
    emergency_override=True,  # Allows dispensing without payment
    dispensing_notes='Emergency dispensing - life-threatening condition',
)

# ❌ Invalid: Billing not paid, no emergency flag
prescription = dispense_prescription(
    prescription=prescription,  # Billing status: PENDING
    pharmacist=pharmacist,
    emergency_override=False,  # Will raise ValidationError
)
```

## Error Handling

### Clear Exception Messages

All validation errors include:
- **What** went wrong (the rule violated)
- **Why** it matters (Nigerian clinic context)
- **How** to fix it (actionable guidance)
- **Context** (IDs, statuses, amounts)

### Example Error Messages

**LabOrder without Consultation:**
```
"Lab orders require a consultation. Per Nigerian clinic operational rules, 
all lab orders must have clinical context from a consultation. 
Please ensure a consultation exists for this visit."
```

**Result Posting without Active Order:**
```
"Lab results can only be posted for active lab orders. 
Current order status: 'RESULT_READY'. Order ID: 123. 
Please ensure the lab order is in ORDERED or SAMPLE_COLLECTED status before posting results."
```

**Dispensing without Payment:**
```
"Prescription cannot be dispensed until billing is paid. 
Current billing status: PENDING. Outstanding amount: ₦5,000.00. 
Please process payment before dispensing. 
For emergency cases, use the emergency override flag."
```

## Testing

### Test Coverage

All governance rules should be tested:
- Model validation tests
- Database constraint tests
- Service function tests
- Error message clarity tests

### Test Examples

```python
def test_lab_order_requires_consultation(self):
    """Test that LabOrder cannot be created without consultation."""
    with self.assertRaises(ValidationError) as cm:
        LabOrder.objects.create(
            visit=visit,
            consultation=None,  # Missing consultation
            ordered_by=doctor,
            tests_requested=['CBC'],
        )
    self.assertIn('consultation', str(cm.exception).lower())

def test_lab_result_requires_active_order(self):
    """Test that LabResult cannot be posted for inactive order."""
    lab_order.status = 'RESULT_READY'
    lab_order.save()
    
    with self.assertRaises(ValidationError) as cm:
        LabResult.objects.create(
            lab_order=lab_order,  # Inactive order
            result_data='Normal',
            recorded_by=lab_tech,
        )
    self.assertIn('active', str(cm.exception).lower())

def test_prescription_dispensing_requires_payment(self):
    """Test that prescription cannot be dispensed without payment."""
    with self.assertRaises(ValidationError) as cm:
        dispense_prescription(
            prescription=prescription,  # Billing not paid
            pharmacist=pharmacist,
            emergency_override=False,
        )
    self.assertIn('payment', str(cm.exception).lower())
```

## Compliance

### Nigerian Clinic Operational Realities

These rules align with:
- **Clinical Workflow:** Proper documentation and traceability
- **Billing Integration:** Payment clearance before service delivery
- **Emergency Protocols:** Life-threatening situations require immediate action
- **Audit Requirements:** Clear audit trail for all clinical actions
- **Regulatory Compliance:** Proper documentation for regulatory bodies

### Regulatory Alignment

- **Nigerian Medical and Dental Council (NMDC):** Proper clinical documentation
- **National Health Insurance Scheme (NHIS):** Billing and payment tracking
- **Pharmacy Council of Nigeria (PCN):** Prescription dispensing protocols
- **Laboratory Accreditation:** Result posting and order tracking

## Future Enhancements

- Role-based emergency authorization levels
- Emergency override audit logging
- Automated compliance reporting
- Integration with regulatory reporting systems


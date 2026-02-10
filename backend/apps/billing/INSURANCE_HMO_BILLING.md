# Insurance/HMO Billing Implementation

## Overview

This document describes the Insurance/HMO billing logic implementation for the Nigerian EMR system.

## Models

### InsuranceProvider
- Stores insurance provider information
- Fields: name, code, contact details, address, is_active

### InsurancePolicy
- Links patient to insurance provider
- Fields: patient, provider, policy_number, coverage_type, coverage_percentage, validity dates
- Method: `is_valid()` - checks if policy is currently valid

## Visit Payment Type

### Payment Type Field
Visits now have a `payment_type` field:
- **CASH**: Standard cash payment visit
- **INSURANCE**: Insurance/HMO visit

### Visit Creation Flow

**POST** `/api/v1/visits/`

**Payload:**
```json
{
    "patient": 1,
    "payment_type": "INSURANCE",  // or "CASH"
    "visit_type": "CONSULTATION",
    "chief_complaint": "Headache"
}
```

**Behavior:**
- If `payment_type` is `INSURANCE`:
  - Visit `payment_status` is set to `INSURANCE_PENDING`
  - Bill is created as insurance-backed (`is_insurance_backed=True`)
  - Bill status is set to `INSURANCE_PENDING`
  - If patient has an active insurance policy, it's automatically linked

- If `payment_type` is `CASH`:
  - Visit `payment_status` is set to `UNPAID`
  - Bill is created as cash payment (`is_insurance_backed=False`)
  - Bill status is set to `UNPAID`

## Insurance Visit Rules

### Bill Items
- **Automatic Marking**: When bill items are added to an insurance visit, they are automatically marked as `INSURANCE` status
- **No Manual Entry**: Departments cannot manually set item status - it's determined by visit payment type

### Payment Requirements
- **No Immediate Payment**: Insurance visits do not require immediate payment
- **Payment Gating**: Clinical actions are allowed for insurance visits (payment_status can be INSURANCE_PENDING)

### Receipts vs Invoices
- **Cash Visits**: Generate receipts
- **Insurance Visits**: Generate invoices (not receipts)

### Bill Status
- Insurance bills start with status: `INSURANCE_PENDING`
- Cannot accept Paystack/Cash payments (only POS, TRANSFER, WALLET, INSURANCE)

## Insurance Claim Submission

### Endpoint

**POST** `/api/billing/insurance/submit-claim/`

**Payload:**
```json
{
    "bill_id": 1,
    "insurance_provider": "Health Insurance Co.",
    "policy_number": "POL-123456"
}
```

**Behavior:**
1. Validates bill exists
2. Validates visit is OPEN
3. Gets or creates insurance provider
4. Gets or creates insurance policy for patient
5. Marks bill as insurance-backed
6. Links insurance policy to bill
7. Marks all bill items as INSURANCE
8. Updates bill status to INSURANCE_PENDING (if not already claimed)
9. Updates visit payment_status to INSURANCE_PENDING

**Response:**
```json
{
    "bill_id": 1,
    "visit_id": 1,
    "insurance_provider": "Health Insurance Co.",
    "policy_number": "POL-123456",
    "bill_status": "INSURANCE_PENDING",
    "visit_payment_status": "INSURANCE_PENDING",
    "is_insurance_backed": true,
    "policy_created": false,
    "items_marked_as_insurance": 3
}
```

## State Flow

### Insurance Bill Status Flow

```
INSURANCE_PENDING → INSURANCE_CLAIMED → SETTLED
```

### Status Transitions

1. **INSURANCE_PENDING**
   - Initial state when insurance visit is created
   - Bill items are marked as INSURANCE
   - No payment required yet
   - Clinical actions are allowed

2. **INSURANCE_CLAIMED**
   - Claim has been submitted to insurance provider
   - Waiting for insurance payment/approval
   - Can be updated via `/api/billing/insurance/update-claim-status/`

3. **SETTLED**
   - Insurance claim has been settled
   - Visit can be closed
   - Final state for insurance bills

### Update Claim Status

**POST** `/api/billing/insurance/update-claim-status/`

**Payload:**
```json
{
    "bill_id": 1,
    "status": "INSURANCE_CLAIMED"  // or "SETTLED"
}
```

**Valid Transitions:**
- `INSURANCE_PENDING` → `INSURANCE_CLAIMED`
- `INSURANCE_CLAIMED` → `SETTLED`

## Bill Item Status

### Status Values
- **UNPAID**: Cash visit items (default for cash visits)
- **PAID**: Items that have been paid
- **INSURANCE**: Insurance visit items (automatic for insurance visits)

### Automatic Status Assignment
- Cash visits: Items default to `UNPAID`
- Insurance visits: Items default to `INSURANCE`
- When insurance claim is submitted: All items are marked as `INSURANCE`

## Workflow Examples

### Example 1: Insurance Visit Creation

```python
# 1. Create insurance visit
POST /api/v1/visits/
{
    "patient": 1,
    "payment_type": "INSURANCE",
    "visit_type": "CONSULTATION"
}

# Response: Visit created with payment_status=INSURANCE_PENDING
# Bill created with is_insurance_backed=True, status=INSURANCE_PENDING

# 2. Add bill items (automatically marked as INSURANCE)
POST /api/billing/add-item/
{
    "visit_id": 1,
    "department": "LAB",
    "service_code": "CBC-001"
}

# Bill item created with status=INSURANCE

# 3. Submit insurance claim
POST /api/billing/insurance/submit-claim/
{
    "bill_id": 1,
    "insurance_provider": "Health Insurance Co.",
    "policy_number": "POL-123456"
}

# All items marked as INSURANCE
# Bill status remains INSURANCE_PENDING
```

### Example 2: Cash Visit Creation

```python
# 1. Create cash visit
POST /api/v1/visits/
{
    "patient": 1,
    "payment_type": "CASH",
    "visit_type": "CONSULTATION"
}

# Response: Visit created with payment_status=UNPAID
# Bill created with is_insurance_backed=False, status=UNPAID

# 2. Add bill items (automatically marked as UNPAID)
POST /api/billing/add-item/
{
    "visit_id": 1,
    "department": "LAB",
    "service_code": "CBC-001"
}

# Bill item created with status=UNPAID

# 3. Process payment
POST /api/billing/payments/
{
    "bill_id": 1,
    "amount": "5000.00",
    "payment_method": "POS"
}

# Bill status updated to PARTIALLY_PAID or PAID
```

## API Endpoints

### Insurance Claim Management

1. **Submit Insurance Claim**
   - `POST /api/billing/insurance/submit-claim/`
   - Requires: bill_id, insurance_provider, policy_number
   - Permission: Receptionist only

2. **Update Claim Status**
   - `POST /api/billing/insurance/update-claim-status/`
   - Requires: bill_id, status
   - Permission: Receptionist only

### Visit Creation

- `POST /api/v1/visits/`
- New field: `payment_type` (CASH or INSURANCE)
- Auto-creates insurance-backed bill for insurance visits

### Bill Item Creation

- `POST /api/billing/add-item/`
- Automatically marks items as INSURANCE for insurance visits
- Automatically marks items as UNPAID for cash visits

## Validation Rules

### Insurance Visit Validation
- Visit must be OPEN to submit claim
- Bill must exist
- Insurance provider must be provided
- Policy number must be provided

### Status Transition Validation
- Only valid transitions are allowed
- Cannot skip states (e.g., INSURANCE_PENDING → SETTLED)
- Must follow: INSURANCE_PENDING → INSURANCE_CLAIMED → SETTLED

### Payment Method Validation
- Insurance bills cannot accept Paystack/Cash
- Only POS, TRANSFER, WALLET, INSURANCE methods allowed

## Database Migrations

Migration file: `0004_add_payment_type_and_insurance_claim.py`

To apply:
```bash
python manage.py migrate visits
```

## Integration Notes

1. **Visit Creation**: Receptionist selects payment type (CASH or INSURANCE) when creating visit
2. **Bill Item Creation**: Items are automatically marked based on visit payment type
3. **Claim Submission**: Receptionist submits insurance claim with provider and policy number
4. **Status Updates**: Receptionist updates claim status as it progresses through the workflow
5. **Invoice Generation**: Insurance bills generate invoices instead of receipts

## Security

- Only Receptionist can submit/update insurance claims
- All actions are logged to AuditLog
- Visit must be OPEN to submit claims
- State transitions are validated


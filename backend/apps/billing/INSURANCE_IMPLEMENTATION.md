# HMO/Insurance Billing Implementation

## Overview

This implementation adds HMO/Insurance billing support to the Rule-Locked Nigerian EMR system. Insurance **does NOT bypass billing**; it alters payment responsibility while maintaining strict enforcement rules.

## Key Principles

1. **Visit-Scoped**: All insurance data MUST be visit-scoped
2. **Payment Enforcement**: Clinical actions still require `payment_status == CLEARED`
3. **Payment Responsibility**: Insurance alters who pays, not whether payment is required
4. **CLEARED Status**: Visit can be CLEARED with ₦0 patient payment when insurance covers full amount
5. **Receptionist-Only**: Only Receptionists can manage insurance data

## Models

### HMOProvider

Stores insurance provider information:
- `name`: Provider name (unique)
- `code`: Provider code/identifier (optional, unique)
- `contact_person`, `contact_phone`, `contact_email`, `address`: Contact information
- `is_active`: Whether provider is currently active
- `created_by`: Receptionist who created the provider

**Endpoint**: `/api/v1/billing/hmo-providers/`

### VisitInsurance

Visit-scoped insurance coverage record:
- `visit`: OneToOneField to Visit (MUST be visit-scoped)
- `provider`: ForeignKey to HMOProvider
- `policy_number`: Patient's insurance policy number
- `coverage_type`: FULL or PARTIAL
- `coverage_percentage`: Coverage percentage (0-100, 100 for FULL)
- `approval_status`: PENDING, APPROVED, or REJECTED
- `approved_amount`: Amount approved by insurance (when APPROVED)
- `approval_reference`: Insurance approval reference number
- `approval_date`: Date of approval
- `rejection_reason`: Reason for rejection (when REJECTED)
- `created_by`: Receptionist who created the record

**Endpoint**: `/api/v1/visits/{visit_id}/insurance/`

## Coverage Computation

### FULL Coverage

- `coverage_percentage` must be 100
- Insurance covers entire amount (up to `approved_amount` if set)
- Patient payable = `total_charges - insurance_amount`
- If `patient_payable == 0`, visit can be CLEARED with ₦0 patient payment

### PARTIAL Coverage

- `coverage_percentage` is between 0 and 100
- Insurance covers: `total_charges * coverage_percentage / 100` (up to `approved_amount` if set)
- Patient payable = `total_charges - insurance_amount`
- Patient must pay their portion

## Billing Logic

### Payment Clearing with Insurance

Visit payment can be CLEARED when:

1. **Insurance covers all** (`patient_payable == 0`):
   - Insurance status: APPROVED
   - Coverage type: FULL
   - Insurance amount >= total charges
   - Result: `payment_status = CLEARED` with ₦0 patient payment

2. **Patient pays their portion**:
   - Insurance status: APPROVED
   - Coverage type: FULL or PARTIAL
   - Total payments >= patient_payable
   - Result: `payment_status = CLEARED`

3. **No insurance**:
   - Standard payment clearing
   - Total payments >= total charges
   - Result: `payment_status = CLEARED`

### Example Scenarios

#### Scenario 1: FULL Coverage, Insurance Approved

```
Total Charges: ₦10,000
Insurance: FULL coverage, APPROVED, approved_amount: ₦10,000
Computation:
  - Insurance amount: ₦10,000
  - Patient payable: ₦0.00
  - is_fully_covered: True

Result: payment_status = CLEARED (₦0 patient payment)
```

#### Scenario 2: PARTIAL Coverage, Insurance Approved

```
Total Charges: ₦10,000
Insurance: PARTIAL coverage (80%), APPROVED, approved_amount: ₦8,000
Computation:
  - Insurance amount: ₦8,000
  - Patient payable: ₦2,000
  - is_fully_covered: False

Result: payment_status = CLEARED when patient pays ₦2,000
```

#### Scenario 3: Insurance PENDING

```
Total Charges: ₦10,000
Insurance: FULL coverage, PENDING
Computation:
  - Insurance amount: ₦0.00
  - Patient payable: ₦10,000
  - is_fully_covered: False

Result: payment_status = PENDING until insurance is APPROVED or patient pays full amount
```

#### Scenario 4: Insurance REJECTED

```
Total Charges: ₦10,000
Insurance: FULL coverage, REJECTED
Computation:
  - Insurance amount: ₦0.00
  - Patient payable: ₦10,000
  - is_fully_covered: False

Result: payment_status = PENDING until patient pays full amount
```

## Enforcement Rules

### Role-Based Access

- **Receptionist**: Can create, read, update HMO providers and visit insurance
- **Other roles**: Read-only access to insurance information

### Visit Status Enforcement

- Insurance can only be created/updated for OPEN visits
- CLOSED visits are immutable (insurance read-only)

### Payment Enforcement

- Clinical actions (Consultation, Lab, Radiology, Prescription) still require `payment_status == CLEARED`
- Insurance does NOT bypass this requirement
- Insurance only changes who pays (insurance vs patient)

### Audit Logging

All insurance actions are logged to AuditLog:
- `HMO_PROVIDER_CREATED`
- `HMO_PROVIDER_UPDATED`
- `VISIT_INSURANCE_CREATED`
- `VISIT_INSURANCE_UPDATED`
- `VISIT_INSURANCE_READ`

## API Endpoints

### HMO Provider Management

```
GET    /api/v1/billing/hmo-providers/          # List providers
POST   /api/v1/billing/hmo-providers/          # Create provider (Receptionist)
GET    /api/v1/billing/hmo-providers/{id}/      # Retrieve provider
PUT    /api/v1/billing/hmo-providers/{id}/     # Update provider (Receptionist)
PATCH  /api/v1/billing/hmo-providers/{id}/      # Partial update (Receptionist)
DELETE /api/v1/billing/hmo-providers/{id}/      # Delete provider (Receptionist)
```

### Visit Insurance Management

```
GET    /api/v1/visits/{visit_id}/insurance/          # List insurance (should be single)
POST   /api/v1/visits/{visit_id}/insurance/          # Create insurance (Receptionist)
GET    /api/v1/visits/{visit_id}/insurance/{id}/    # Retrieve insurance
PUT    /api/v1/visits/{visit_id}/insurance/{id}/     # Update insurance (Receptionist)
PATCH  /api/v1/visits/{visit_id}/insurance/{id}/     # Partial update (Receptionist)
DELETE /api/v1/visits/{visit_id}/insurance/{id}/      # Forbidden (compliance)
```

## Implementation Status

✅ **Completed:**
- HMOProvider model
- VisitInsurance model (visit-scoped)
- Coverage computation logic (FULL and PARTIAL)
- Serializers with validation
- ViewSets with Receptionist-only enforcement
- URL routing (visit-scoped)
- Admin interface
- Audit logging
- Visit model integration

⚠️ **Note:**
- Total charges calculation currently uses placeholder (would need VisitCharge model)
- Full implementation would calculate charges from VisitCharge records
- Current implementation allows insurance to work with existing payment system

## Compliance Checklist

✅ **Visit-Scoped**: All insurance data is visit-scoped  
✅ **Payment Enforcement**: Clinical actions still require payment_status == CLEARED  
✅ **Receptionist-Only**: Only Receptionists can manage insurance  
✅ **Audit Logging**: All actions logged to AuditLog  
✅ **No Bypass**: Insurance does NOT bypass billing rules  
✅ **CLEARED with ₦0**: Visit can be CLEARED when insurance covers full amount  

## Future Enhancements

1. **VisitCharge Model**: Implement charge tracking for accurate total calculation
2. **Insurance Claims**: Add insurance claim submission workflow
3. **Coverage Limits**: Add per-visit or per-year coverage limits
4. **Co-payment**: Add co-payment amount field
5. **Deductible**: Add deductible amount handling

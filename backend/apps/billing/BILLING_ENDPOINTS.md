# Visit-Nested Billing Endpoints

## Overview

Unified billing API endpoints for visit-scoped billing operations. All billing mutations are Receptionist-only, and closed visits are read-only.

## Endpoints

All endpoints are nested under `/api/v1/visits/{visit_id}/billing/`

### 1. GET Billing Summary

**Endpoint**: `GET /api/v1/visits/{visit_id}/billing/summary/`

**Authentication**: Authenticated users

**Description**: Get complete billing summary for a Visit using centralized BillingService.

**Response**:
```json
{
  "total_charges": "10000.00",
  "total_payments": "5000.00",
  "total_wallet_debits": "2000.00",
  "has_insurance": true,
  "insurance_status": "APPROVED",
  "insurance_amount": "3000.00",
  "insurance_coverage_type": "PARTIAL",
  "patient_payable": "7000.00",
  "outstanding_balance": "0.00",
  "payment_status": "CLEARED",
  "is_fully_covered_by_insurance": false,
  "can_be_cleared": true,
  "computation_timestamp": "2024-01-15T10:30:00Z",
  "visit_id": 123
}
```

**Audit Log**: `BILLING_SUMMARY_VIEWED`

---

### 2. POST Create Charge (MISC)

**Endpoint**: `POST /api/v1/visits/{visit_id}/billing/charges/`

**Authentication**: Receptionist only

**Description**: Create a MISC charge for a Visit. Only MISC category allowed for manual creation (other charges are system-generated).

**Request Body**:
```json
{
  "amount": "5000.00",
  "description": "Additional service fee"
}
```

**Validation Rules**:
- `amount` (required): Must be > 0
- `description` (required): Non-empty string
- Visit must be OPEN
- Only Receptionist can create charges

**Response**:
```json
{
  "id": 456,
  "visit_id": 123,
  "category": "MISC",
  "description": "Additional service fee",
  "amount": "5000.00",
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Audit Log**: `BILLING_CHARGE_CREATED`

---

### 3. POST Create Payment

**Endpoint**: `POST /api/v1/visits/{visit_id}/billing/payments/`

**Authentication**: Receptionist only

**Description**: Create a payment for a Visit. Supports all payment methods (CASH, CARD, BANK_TRANSFER, etc.).

**Request Body**:
```json
{
  "amount": "5000.00",
  "payment_method": "CASH",
  "transaction_reference": "REF123456",
  "notes": "Payment received",
  "status": "CLEARED"
}
```

**Validation Rules**:
- `amount` (required): Must be > 0
- `payment_method` (required): One of CASH, CARD, BANK_TRANSFER, MOBILE_MONEY, INSURANCE, WALLET, PAYSTACK
- `status` (optional): Defaults to PENDING
- Visit must be OPEN
- Only Receptionist can create payments

**Response**: PaymentSerializer data

**Audit Log**: `BILLING_PAYMENT_CREATED`

**Note**: Visit payment_status is automatically updated based on billing summary.

---

### 4. POST Create Wallet Debit

**Endpoint**: `POST /api/v1/visits/{visit_id}/billing/wallet-debit/`

**Authentication**: Receptionist only

**Description**: Create a wallet debit payment for a Visit. Creates both WalletTransaction and Payment records.

**Request Body**:
```json
{
  "wallet_id": 789,
  "amount": "3000.00",
  "description": "Payment for visit 123"
}
```

**Validation Rules**:
- `wallet_id` (required): Valid wallet ID
- `amount` (required): Must be > 0
- `description` (optional): Defaults to "Payment for visit {visit_id}"
- Visit must be OPEN
- Wallet must have sufficient balance
- Only Receptionist can create wallet debits

**Response**:
```json
{
  "wallet_transaction": {
    "id": 101,
    "amount": "3000.00",
    "balance_after": "7000.00",
    "status": "COMPLETED"
  },
  "payment": {
    "id": 202,
    "amount": "3000.00",
    "status": "CLEARED"
  },
  "outstanding_balance": "2000.00",
  "visit_payment_status": "PARTIAL"
}
```

**Audit Log**: `BILLING_WALLET_DEBIT_CREATED`

**Note**: 
- Creates WalletTransaction (DEBIT, COMPLETED)
- Creates Payment record (WALLET, CLEARED)
- Visit payment_status is automatically updated

---

### 5. POST Create Insurance

**Endpoint**: `POST /api/v1/visits/{visit_id}/billing/insurance/`

**Authentication**: Receptionist only

**Description**: Create insurance record for a Visit. Uses existing VisitInsurance model.

**Request Body**:
```json
{
  "provider": 1,
  "policy_number": "POL123456",
  "coverage_type": "FULL",
  "coverage_percentage": 100,
  "notes": "Insurance coverage for visit"
}
```

**Validation Rules**:
- `provider` (required): Valid HMO Provider ID
- `policy_number` (required): Non-empty string
- `coverage_type` (required): FULL or PARTIAL
- `coverage_percentage` (required): 0-100, must be 100 for FULL
- Visit must be OPEN
- Only Receptionist can create insurance records

**Response**: VisitInsuranceSerializer data

**Audit Log**: `BILLING_INSURANCE_CREATED`

---

## Permission Rules

### Read Operations (GET)
- **Permission**: `IsAuthenticated`
- **Access**: All authenticated users can view billing summary

### Write Operations (POST)
- **Permission**: `CanProcessPayment` + `IsVisitOpen`
- **Access**: Only Receptionists can create billing records
- **Restriction**: Visit must be OPEN (closed visits are read-only)

## Validation Rules

### Visit Scope Enforcement
- All endpoints require `visit_id` in URL
- Visit must exist
- Visit must be OPEN for mutations (GET allowed for CLOSED visits)

### Closed Visit Protection
- CLOSED visits are billing read-only
- Mutations (POST) are rejected with `403 Forbidden`
- Error message: "Cannot modify billing for a CLOSED visit. Closed visits are billing read-only per EMR rules."

### Role Enforcement
- Only Receptionists can create billing records
- Other roles receive `403 Forbidden`
- Error message: "Only Receptionists can process billing operations."

## Audit Logging

All billing operations are logged to AuditLog:

| Action | Audit Log Action | Resource Type |
|--------|-----------------|---------------|
| View Summary | `BILLING_SUMMARY_VIEWED` | billing |
| Create Charge | `BILLING_CHARGE_CREATED` | visit_charge |
| Create Payment | `BILLING_PAYMENT_CREATED` | payment |
| Create Wallet Debit | `BILLING_WALLET_DEBIT_CREATED` | wallet_transaction |
| Create Insurance | `BILLING_INSURANCE_CREATED` | visit_insurance |

## Integration with BillingService

All billing computations use the centralized `BillingService`:

- **Billing Summary**: Uses `BillingService.compute_billing_summary()`
- **Payment Validation**: Uses `BillingService.validate_payment_amount()`
- **Status Updates**: Visit payment_status updated based on billing summary

## Error Responses

### 400 Bad Request
- Invalid request data
- Validation errors
- Insufficient wallet balance

### 403 Forbidden
- Non-Receptionist attempting mutation
- Attempting to modify CLOSED visit
- Visit not OPEN

### 404 Not Found
- Visit does not exist
- Wallet does not exist

## Example Usage

### Get Billing Summary
```bash
GET /api/v1/visits/123/billing/summary/
Authorization: Bearer <token>
```

### Create MISC Charge
```bash
POST /api/v1/visits/123/billing/charges/
Authorization: Bearer <receptionist_token>
Content-Type: application/json

{
  "amount": "5000.00",
  "description": "Additional service fee"
}
```

### Create Payment
```bash
POST /api/v1/visits/123/billing/payments/
Authorization: Bearer <receptionist_token>
Content-Type: application/json

{
  "amount": "5000.00",
  "payment_method": "CASH",
  "status": "CLEARED"
}
```

### Create Wallet Debit
```bash
POST /api/v1/visits/123/billing/wallet-debit/
Authorization: Bearer <receptionist_token>
Content-Type: application/json

{
  "wallet_id": 789,
  "amount": "3000.00"
}
```

### Create Insurance
```bash
POST /api/v1/visits/123/billing/insurance/
Authorization: Bearer <receptionist_token>
Content-Type: application/json

{
  "provider": 1,
  "policy_number": "POL123456",
  "coverage_type": "FULL",
  "coverage_percentage": 100
}
```

## Compliance Checklist

✅ **Visit-Scoped**: All endpoints require visit_id in URL  
✅ **Receptionist-Only**: Mutations require Receptionist role  
✅ **Closed Visit Protection**: CLOSED visits are read-only  
✅ **Audit Logging**: All actions logged to AuditLog  
✅ **BillingService Integration**: Uses centralized billing service  
✅ **Validation**: Comprehensive validation rules  
✅ **Error Handling**: Proper error responses  


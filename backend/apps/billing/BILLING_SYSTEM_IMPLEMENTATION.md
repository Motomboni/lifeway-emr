# Nigerian EMR Billing System Implementation

## Overview

This document describes the comprehensive billing system implementation for the Nigerian EMR, following all system principles and rules.

## System Principles Implemented

✅ **Visit-Scoped Billing**: All billing operations are tied to a specific Visit
✅ **No Visit = No Bill**: Charges and payments require a Visit
✅ **No Consultation = No Departmental Charge**: Charges are system-generated from clinical actions
✅ **Departments Generate Billable Items**: Lab, Pharmacy, Radiology, Procedures all generate charges
✅ **Only Receptionist Handles Payments**: Payment processing restricted to Receptionist role
✅ **Doctor Never Handles Money**: Doctors only create consultations/orders
✅ **Payments May Be Partial**: Supports partial payments
✅ **Insurance/HMO Payments Are Deferred**: Insurance flow separate from standard payment
✅ **Multiple Payment Modes**: CASH, POS, TRANSFER, PAYSTACK, WALLET, INSURANCE
✅ **Append-Only Financial Records**: No deletions, all records immutable once created

## Payment Modes

The system supports the following payment modes (Nigerian context):

1. **CASH**: Cash payment
2. **POS**: Point of Sale (card payment)
3. **TRANSFER**: Bank transfer
4. **PAYSTACK**: Online payment via Paystack
5. **WALLET**: Patient wallet debit
6. **INSURANCE**: Insurance/HMO coverage

## Bill Status Flow

### Standard Payment Flow
```
UNPAID → PARTIALLY_PAID → PAID
```

- **UNPAID**: No payment made, outstanding balance > 0
- **PARTIALLY_PAID**: Partial payment made, outstanding balance > 0
- **PAID**: Full payment made, outstanding balance <= 0

### Insurance/HMO Flow
```
INSURANCE_PENDING → INSURANCE_CLAIMED → SETTLED
```

- **INSURANCE_PENDING**: Insurance exists but not approved, patient must pay full amount
- **INSURANCE_CLAIMED**: Insurance approved, waiting for patient portion (if any)
- **SETTLED**: Insurance approved and fully paid (patient portion if any)

## Visit Closure Rules

- Visit **CANNOT** be closed with outstanding balance
- Payment status must be **PAID** or **SETTLED**
- Exception: Insurance visits can be **SETTLED** with ₦0 patient payment (fully covered by insurance)

## Models Updated

### Payment Model
- Updated `PAYMENT_METHOD_CHOICES` to match Nigerian payment modes
- Payment methods: CASH, POS, TRANSFER, PAYSTACK, WALLET, INSURANCE
- Payment status: PENDING, PARTIAL, CLEARED, FAILED, REFUNDED

### Visit Model
- Updated `payment_status` field to support new status flow:
  - Standard: UNPAID, PARTIALLY_PAID, PAID
  - Insurance: INSURANCE_PENDING, INSURANCE_CLAIMED, SETTLED
- Updated `is_payment_cleared()` to check for 'PAID' or 'SETTLED'

### VisitCharge Model
- System-generated charges for:
  - CONSULTATION
  - LAB
  - RADIOLOGY
  - DRUG
  - PROCEDURE
  - MISC

## Services

### BillingService
Centralized billing computation service that:
- Computes total charges, payments, wallet debits
- Calculates insurance coverage
- Determines patient payable amount
- Computes outstanding balance
- Determines payment status (UNPAID, PARTIALLY_PAID, PAID, INSURANCE_PENDING, INSURANCE_CLAIMED, SETTLED)
- Validates visit closure eligibility

### ReceiptService
Service for generating financial documents:
- **Receipt**: Generated for patient payments (CASH, POS, TRANSFER, PAYSTACK, WALLET)
- **Invoice**: Generated for insurance/HMO claims
- **Billing Statement**: Complete billing statement with all charges, payments, insurance, and wallet transactions

## API Endpoints

### Billing Endpoints (Visit-Scoped)
- `GET /api/v1/visits/{visit_id}/billing/summary/` - Get billing summary
- `GET /api/v1/visits/{visit_id}/billing/charges/` - List charges
- `POST /api/v1/visits/{visit_id}/billing/charges/` - Create MISC charge
- `POST /api/v1/visits/{visit_id}/billing/payments/` - Create payment
- `POST /api/v1/visits/{visit_id}/billing/wallet-debit/` - Debit wallet
- `GET /api/v1/visits/{visit_id}/billing/insurance/` - Get insurance
- `POST /api/v1/visits/{visit_id}/billing/insurance/` - Create insurance
- `PATCH /api/v1/visits/{visit_id}/billing/insurance/` - Update insurance (approval)

### Receipt/Invoice Endpoints
- `GET /api/v1/visits/{visit_id}/billing/receipt/` - Generate receipt for all payments
- `POST /api/v1/visits/{visit_id}/billing/receipt/` - Generate receipt for specific payment
- `GET /api/v1/visits/{visit_id}/billing/invoice/` - Generate invoice for insurance claim
- `GET /api/v1/visits/{visit_id}/billing/statement/` - Generate complete billing statement

## Clinical Models Updated

- **Laboratory**: Updated payment checks to allow 'PAID' or 'SETTLED'
- **Radiology**: Updated payment checks to allow 'PAID' or 'SETTLED'

## Database Migrations

Two migration files created:
1. `billing/migrations/0007_update_payment_status_flow.py` - Updates Payment model payment_method choices
2. `visits/migrations/0003_update_payment_status_flow.py` - Updates Visit model payment_status choices

**Important**: Run migrations before deploying:
```bash
python manage.py migrate billing visits
```

## Frontend Updates Required

The frontend needs to be updated to:
1. Display new payment statuses (UNPAID, PARTIALLY_PAID, PAID, INSURANCE_PENDING, INSURANCE_CLAIMED, SETTLED)
2. Update payment method options (CASH, POS, TRANSFER, PAYSTACK, WALLET, INSURANCE)
3. Add receipt/invoice generation UI
4. Update payment status checks to use 'PAID' or 'SETTLED' instead of 'CLEARED'
5. Display billing statements

## Testing Checklist

- [ ] Test standard payment flow: UNPAID → PARTIALLY_PAID → PAID
- [ ] Test insurance flow: INSURANCE_PENDING → INSURANCE_CLAIMED → SETTLED
- [ ] Test visit closure with PAID status
- [ ] Test visit closure with SETTLED status (insurance)
- [ ] Test visit closure rejection with outstanding balance
- [ ] Test all payment modes (CASH, POS, TRANSFER, PAYSTACK, WALLET, INSURANCE)
- [ ] Test receipt generation
- [ ] Test invoice generation
- [ ] Test billing statement generation
- [ ] Test clinical action blocking when payment not PAID/SETTLED
- [ ] Test Receptionist-only payment processing
- [ ] Test audit logging for all billing actions

## Next Steps

1. **Run Migrations**: Apply database migrations
2. **Update Frontend**: Update React components to handle new payment statuses
3. **Test**: Run comprehensive tests
4. **Documentation**: Update user manual with new payment flows
5. **Training**: Train Receptionists on new payment modes and statuses

## Notes

- All financial records are append-only (no deletions)
- Payment records are immutable once verified
- Insurance does not bypass payment enforcement; it alters payment responsibility
- Clinical actions require payment_status == 'PAID' or 'SETTLED'
- Visit closure requires payment_status == 'PAID' or 'SETTLED' AND outstanding_balance <= 0


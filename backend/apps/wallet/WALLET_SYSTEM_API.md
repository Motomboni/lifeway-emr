# Patient Wallet System API

## Overview

This document describes the Patient Wallet System API endpoints for wallet top-up and payment processing.

## Models

### Wallet (OneToOne with Patient)
- Each patient has exactly one wallet
- Auto-created when patient is created
- Tracks balance in NGN
- Balance cannot go negative

### WalletTransaction (Immutable)
- Records all wallet operations
- Transaction types: CREDIT, DEBIT
- Status: PENDING, COMPLETED, FAILED, CANCELLED
- Immutable (append-only, no edits/deletes)

## Rules

### Wallet Balance
- **Cannot go negative**: All debit operations validate sufficient balance
- **Atomic operations**: Balance updates are atomic with transaction creation

### WalletTransaction
- **Immutable**: Once created, cannot be modified or deleted
- **Visit-referenced**: DEBIT transactions must reference a Visit
- **Audited**: All transactions are logged

### Wallet Payment
- **Full or partial**: Can pay full outstanding balance or partial amount
- **Bill status update**: Automatically updates Bill status
- **Dual records**: Creates both WalletTransaction and BillPayment records

## API Endpoints

### 1. Wallet Top-Up

**POST** `/api/v1/wallet/topup/`

**Payload:**
```json
{
    "patient_id": 1,
    "amount": "10000.00",
    "description": "Wallet top-up via cash"
}
```

**Behavior:**
1. Validates patient exists
2. Gets or creates wallet for patient
3. Credits wallet balance
4. Creates WalletTransaction (CREDIT)
5. Returns updated wallet balance

**Response:**
```json
{
    "wallet_id": 1,
    "patient_id": 1,
    "amount": "10000.00",
    "new_balance": "10000.00",
    "transaction_id": 1,
    "description": "Wallet top-up via cash"
}
```

**Error Responses:**
- `400 Bad Request`: Invalid amount, missing fields
- `404 Not Found`: Patient not found

### 2. Wallet Payment

**POST** `/api/v1/wallet/pay/`

**Payload:**
```json
{
    "patient_id": 1,
    "visit_id": 1,
    "amount": "5000.00"  // Optional - defaults to outstanding balance
}
```

**Behavior:**
1. Validates patient and visit exist
2. Validates visit belongs to patient
3. Validates visit is OPEN
4. Gets or creates wallet
5. Gets or creates bill for visit
6. Calculates outstanding balance
7. Validates wallet has sufficient balance (prevents negative)
8. Debits wallet (creates WalletTransaction)
9. Creates BillPayment record
10. Updates Bill status
11. Updates Visit payment_status

**Response:**
```json
{
    "wallet_id": 1,
    "patient_id": 1,
    "visit_id": 1,
    "bill_id": 1,
    "amount": "5000.00",
    "wallet_balance": "5000.00",
    "transaction_id": 1,
    "payment_id": 1,
    "bill_status": "PARTIALLY_PAID",
    "outstanding_balance": "10000.00",
    "visit_payment_status": "PARTIALLY_PAID"
}
```

**Error Responses:**
- `400 Bad Request`: Insufficient balance, invalid amount, visit closed
- `404 Not Found`: Patient or visit not found

## Payment Rules

### Full Payment
- If `amount` equals outstanding balance:
  - Bill status → PAID or SETTLED
  - Visit payment_status → PAID or SETTLED

### Partial Payment
- If `amount` is less than outstanding balance:
  - Bill status → PARTIALLY_PAID or INSURANCE_CLAIMED
  - Visit payment_status → PARTIALLY_PAID or INSURANCE_CLAIMED

### Overpayment
- If `amount` exceeds outstanding balance:
  - Allowed (creates credit)
  - Bill status → PAID or SETTLED
  - Outstanding balance becomes negative (credit)

## Workflow Examples

### Example 1: Wallet Top-Up

```python
# POST /api/v1/wallet/topup/
{
    "patient_id": 1,
    "amount": "20000.00",
    "description": "Cash deposit"
}

# Response:
# - Wallet balance updated to 20000.00
# - WalletTransaction (CREDIT) created
# - Transaction is immutable
```

### Example 2: Full Payment

```python
# POST /api/v1/wallet/pay/
{
    "patient_id": 1,
    "visit_id": 1,
    "amount": "15000.00"  // Full outstanding balance
}

# Behavior:
# 1. Wallet debited: 20000.00 → 5000.00
# 2. WalletTransaction (DEBIT) created
# 3. BillPayment created
# 4. Bill status → PAID
# 5. Visit payment_status → PAID
```

### Example 3: Partial Payment

```python
# POST /api/v1/wallet/pay/
{
    "patient_id": 1,
    "visit_id": 1,
    "amount": "5000.00"  // Partial payment
}

# Behavior:
# 1. Wallet debited: 5000.00 → 0.00
# 2. WalletTransaction (DEBIT) created
# 3. BillPayment created
# 4. Bill status → PARTIALLY_PAID
# 5. Visit payment_status → PARTIALLY_PAID
# 6. Outstanding balance: 10000.00 remaining
```

### Example 4: Payment Without Amount (Auto-calculate)

```python
# POST /api/v1/wallet/pay/
{
    "patient_id": 1,
    "visit_id": 1
    // amount not provided - defaults to outstanding balance
}

# Behavior:
# - Amount automatically set to outstanding balance
# - Full payment processed
```

## Validation Rules

### Top-Up Validation
- Patient must exist
- Amount must be greater than zero
- Amount must be valid decimal

### Payment Validation
- Patient must exist
- Visit must exist
- Visit must belong to patient
- Visit must be OPEN
- Wallet must have sufficient balance (prevents negative)
- Amount must be greater than zero (if provided)
- Payment amount must be valid (if provided)

## Negative Balance Prevention

The system enforces negative balance prevention at multiple levels:

1. **Wallet.debit() method**: Checks balance before debiting
2. **WalletPayView**: Validates balance before processing
3. **Database constraint**: Balance field allows negative, but application logic prevents it

If insufficient balance:
- Returns `400 Bad Request` with error message
- No wallet debit occurs
- No payment record created

## Immutability

### WalletTransaction Immutability
- `save()` method prevents updates (raises ValueError if pk exists)
- `delete()` method prevents deletion (raises ValueError)
- All transactions are append-only

### Audit Trail
- All wallet operations are logged to AuditLog
- Transaction history is preserved
- Cannot modify or delete transaction records

## Integration with Bill System

### Bill Payment Flow
1. Wallet payment creates `BillPayment` record
2. Bill totals are recalculated automatically
3. Bill status is updated based on outstanding balance
4. Visit payment_status is updated

### Bill Status Updates
- **UNPAID** → **PARTIALLY_PAID**: When partial payment made
- **UNPAID** → **PAID**: When full payment made
- **PARTIALLY_PAID** → **PAID**: When remaining balance paid
- **INSURANCE_PENDING** → **INSURANCE_CLAIMED**: When partial payment on insurance bill

## Error Handling

### Insufficient Balance
```json
{
    "error": "Insufficient wallet balance. Current balance: 5000.00, Requested amount: 10000.00"
}
```

### Visit Closed
```json
{
    "error": "Cannot pay for a CLOSED visit. Visit must be OPEN."
}
```

### Invalid Patient/Visit
```json
{
    "detail": "Patient with id 999 not found."
}
```

## Security

- Requires authentication
- All operations are logged to AuditLog
- Visit must belong to patient
- Visit must be OPEN
- Wallet balance validated before debit

## Database Tables

- `wallets` - Wallet records
- `wallet_transactions` - Transaction records (immutable)

## Usage Notes

1. **Auto-creation**: Wallet is automatically created if it doesn't exist
2. **Balance tracking**: Balance is updated atomically with transaction creation
3. **Dual records**: Payment creates both WalletTransaction and BillPayment
4. **Status updates**: Bill and Visit statuses are automatically updated
5. **Immutability**: Transactions cannot be modified or deleted


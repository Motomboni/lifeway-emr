# Paystack Payment Gateway Integration

## Overview

This document describes the simplified Paystack payment gateway integration for the EMR system.

## Endpoints

### 1. Initialize Paystack Payment

**POST** `/api/payments/paystack/initiate/`

**Authentication:** Required (Receptionist only)

**Payload:**
```json
{
    "visit_id": 1,
    "amount": "5000.00",
    "callback_url": "https://example.com/callback"  // Optional
}
```

**Response:**
```json
{
    "payment_intent_id": 1,
    "reference": "VISIT-1-ABC123DEF456",
    "authorization_url": "https://checkout.paystack.com/abc123",
    "access_code": "abc123def456",
    "amount": "5000.00",
    "visit_id": 1
}
```

**Rules:**
- Only Receptionist can initiate
- Visit must be OPEN
- Visit must not be insurance-backed (insurance bills cannot accept Paystack)
- System generates unique Paystack reference
- Returns authorization_url for frontend redirect

**Error Responses:**
- `400 Bad Request`: Invalid amount, visit closed, insurance-backed bill
- `403 Forbidden`: User is not a Receptionist
- `404 Not Found`: Visit not found

### 2. Paystack Webhook

**POST** `/api/payments/paystack/webhook/`

**Authentication:** None (public endpoint, signature-verified)

**Headers:**
- `X-Paystack-Signature`: Webhook signature (required)

**Webhook Payload (from Paystack):**
```json
{
    "event": "charge.success",
    "data": {
        "reference": "VISIT-1-ABC123DEF456",
        "status": "success",
        "gateway_response": "Successful",
        "amount": 500000,
        "customer": {
            "email": "customer@example.com"
        },
        "metadata": {
            "visit_id": 1
        }
    }
}
```

**Response:**
```json
{
    "message": "Webhook processed successfully",
    "payment_intent_id": 1,
    "bill_payment_id": 1,
    "bill_status": "PAID",
    "visit_payment_status": "PAID",
    "receipt_number": "REC-1-20240101120000"
}
```

**On Success:**
1. Verify webhook signature
2. Verify transaction server-side (do not trust webhook data alone)
3. Check idempotency (prevent double payment)
4. Create BillPayment record
5. Update Bill totals
6. Update Visit payment_status
7. Generate receipt

**Idempotency:**
- If payment already verified, returns success without processing
- If BillPayment already exists, returns success without creating duplicate

## Payment Flow

### 1. Frontend Initiates Payment

```javascript
// Frontend calls initiate endpoint
const response = await fetch('/api/payments/paystack/initiate/', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        visit_id: 1,
        amount: '5000.00',
        callback_url: 'https://example.com/callback'
    })
});

const data = await response.json();
// Redirect to Paystack checkout
window.location.href = data.authorization_url;
```

### 2. User Completes Payment on Paystack

- User is redirected to Paystack checkout page
- User enters payment details
- Paystack processes payment
- User is redirected to callback_url (if provided)

### 3. Paystack Sends Webhook

- Paystack sends webhook to `/api/payments/paystack/webhook/`
- Webhook signature is verified
- Transaction is verified server-side
- Payment is confirmed

### 4. System Updates

- BillPayment record is created
- Bill totals are recalculated
- Visit payment_status is updated
- Receipt is generated

## Security Features

### 1. Webhook Signature Verification

All webhook requests must include a valid `X-Paystack-Signature` header. The signature is computed using HMAC-SHA512 with the Paystack secret key.

```python
# Signature verification (automatic in webhook handler)
computed_signature = hmac.new(
    secret_key.encode('utf-8'),
    payload,
    hashlib.sha512
).hexdigest()
```

### 2. Server-Side Verification

The webhook handler verifies the transaction with Paystack API before processing. This ensures:
- Transaction is actually successful
- Amount matches expected amount
- Visit ID in metadata matches

### 3. Idempotency Checks

Multiple safeguards prevent double payment:
- PaymentIntent status check (if already VERIFIED, skip)
- BillPayment existence check (if already exists, skip)
- Transaction reference uniqueness (database constraint)

### 4. Visit ID Validation

The webhook validates that the visit_id in Paystack metadata matches the PaymentIntent's visit_id. This prevents:
- Payment for wrong visit
- Payment manipulation
- Cross-visit payment issues

## Integration with Bill System

### BillPayment Creation

When webhook confirms payment:
1. BillPayment record is created with:
   - `bill`: Bill for the visit
   - `amount`: Payment amount
   - `payment_method`: 'PAYSTACK'
   - `transaction_reference`: Paystack reference
   - `processed_by`: User who initiated payment

### Bill Totals Update

After BillPayment creation:
1. Bill totals are recalculated:
   - `total_amount`: Sum of all bill items
   - `amount_paid`: Sum of all payments
   - `outstanding_balance`: total_amount - amount_paid
   - `status`: Updated based on outstanding balance

### Visit Payment Status Update

Visit payment_status is updated based on billing summary:
- `UNPAID`: No payments made
- `PARTIALLY_PAID`: Partial payment made
- `PAID`: Full payment made
- `INSURANCE_PENDING`: Insurance claim pending
- `INSURANCE_CLAIMED`: Insurance claim submitted
- `SETTLED`: Insurance claim settled

## Receipt Generation

After successful payment, a receipt is automatically generated:

```python
receipt_data = ReceiptService.generate_receipt(visit)
```

Receipt includes:
- Receipt number (format: REC-{visit_id}-{timestamp})
- Patient information
- Visit details
- Charges breakdown
- Payment details
- Outstanding balance

## Error Handling

### Webhook Errors

**Invalid Signature:**
```json
{
    "error": "Invalid webhook signature"
}
```
Status: 401

**Transaction Not Found:**
```json
{
    "error": "PaymentIntent not found for reference: VISIT-1-ABC123"
}
```
Status: 404

**Transaction Not Successful:**
```json
{
    "error": "Transaction not successful"
}
```
Status: 400

**Visit ID Mismatch:**
```json
{
    "error": "Security check failed: Visit ID mismatch"
}
```
Status: 400

**Insurance-Backed Bill:**
```json
{
    "error": "Cannot process Paystack payment for insurance-backed bill"
}
```
Status: 400

## Configuration

### Environment Variables

```bash
PAYSTACK_SECRET_KEY=sk_test_...
PAYSTACK_PUBLIC_KEY=pk_test_...
```

### Paystack Dashboard Configuration

1. Go to Paystack Dashboard → Settings → API Keys & Webhooks
2. Add webhook URL: `https://your-domain.com/api/payments/paystack/webhook/`
3. Select events: `charge.success`
4. Copy webhook secret (used for signature verification)

## Testing

### Test Mode

Use Paystack test keys:
- Test Secret Key: `sk_test_...`
- Test Public Key: `pk_test_...`

### Test Cards

- Success: `4084084084084081`
- Decline: `4084084084084085`
- Insufficient Funds: `4084084084084082`

### Webhook Testing

Use Paystack webhook testing tool or ngrok for local testing:

```bash
# Start ngrok
ngrok http 8000

# Update Paystack webhook URL to ngrok URL
# https://abc123.ngrok.io/api/payments/paystack/webhook/
```

## Audit Logging

All Paystack operations are logged:

- **PAYSTACK_PAYMENT_INITIATED**: When payment is initiated
- **PAYSTACK_WEBHOOK_PROCESSED**: When webhook is processed

Log entries include:
- User (if applicable)
- Visit ID
- Payment amount
- Reference
- Bill status
- Visit payment status

## Best Practices

1. **Always verify webhook signature** - Never trust unsigned requests
2. **Always verify server-side** - Do not trust webhook data alone
3. **Check idempotency** - Prevent duplicate processing
4. **Validate visit_id** - Ensure payment is for correct visit
5. **Handle errors gracefully** - Log errors and return appropriate responses
6. **Monitor webhook delivery** - Use Paystack dashboard to monitor webhook status
7. **Test thoroughly** - Test all scenarios before production deployment

## Troubleshooting

### Webhook Not Received

1. Check Paystack dashboard for webhook delivery status
2. Verify webhook URL is correct
3. Check server logs for errors
4. Verify webhook signature is valid

### Payment Not Confirmed

1. Check PaymentIntent status
2. Verify BillPayment was created
3. Check Bill totals were updated
4. Verify Visit payment_status was updated

### Duplicate Payments

1. Check idempotency logic
2. Verify PaymentIntent status check
3. Verify BillPayment existence check
4. Check transaction reference uniqueness

## API Reference

### PaystackInitiateView

- **URL**: `/api/payments/paystack/initiate/`
- **Method**: POST
- **Auth**: Required (Receptionist)
- **Returns**: Payment intent with authorization URL

### paystack_webhook_view

- **URL**: `/api/payments/paystack/webhook/`
- **Method**: POST
- **Auth**: None (signature-verified)
- **Returns**: Webhook processing result


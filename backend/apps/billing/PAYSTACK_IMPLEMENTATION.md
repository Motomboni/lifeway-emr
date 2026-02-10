# Paystack Payment Integration - Visit-Scoped EMR

## Overview

This document describes the Paystack payment processing implementation for the Visit-scoped EMR system. The implementation follows strict security rules to ensure no PHI exposure and server-side verification only.

## Security Rules (Non-Negotiable)

✅ **Visit-Scoped**: All Paystack transactions MUST be visit-scoped  
✅ **No PHI**: No Protected Health Information sent to Paystack  
✅ **Server-Side Verification**: All verification occurs server-side (frontend NOT trusted)  
✅ **Webhook Validation**: All webhooks are signature-verified  
✅ **Idempotency**: Webhook and verification endpoints are idempotent  
✅ **Immutable Records**: Payment records are immutable once verified  

## Architecture

### Models

1. **PaymentIntent** (`billing/models.py`)
   - Tracks Paystack transaction lifecycle
   - Visit-scoped (ForeignKey to Visit)
   - Status: PENDING → INITIALIZED → VERIFIED/FAILED
   - Links to Payment record after verification
   - Immutable after verification

2. **Payment** (existing)
   - Created automatically after PaymentIntent verification
   - Status: CLEARED (Paystack verified = cleared)
   - Immutable once created

### Services

**PaystackVisitService** (`billing/paystack_service.py`)
- `initialize_transaction()`: Initialize Paystack payment (NO PHI)
- `verify_transaction()`: Server-side verification
- `verify_webhook_signature()`: Webhook signature validation
- `is_transaction_successful()`: Check transaction status
- `extract_visit_id_from_metadata()`: Extract visit_id from Paystack response

### API Endpoints

#### 1. Initialize Payment Intent
**POST** `/api/v1/visits/{visit_id}/payment-intents/initialize/`

**Authentication**: Receptionist only  
**Request Body**:
```json
{
  "visit_id": 123,
  "amount": "5000.00",
  "callback_url": "https://example.com/callback",
  "customer_email": "customer@example.com"  // Optional, generic email
}
```

**Response**:
```json
{
  "payment_intent": {
    "id": 1,
    "visit_id": 123,
    "paystack_reference": "VISIT-123-ABC123",
    "amount": "5000.00",
    "status": "INITIALIZED",
    "paystack_authorization_url": "https://checkout.paystack.com/...",
    "paystack_access_code": "abc123"
  },
  "authorization_url": "https://checkout.paystack.com/...",
  "access_code": "abc123",
  "public_key": "pk_test_..."
}
```

**Flow**:
1. Receptionist initiates payment for Visit
2. System generates unique Paystack reference (format: `VISIT-{visit_id}-{uuid}`)
3. Paystack transaction initialized (metadata contains ONLY visit_id, no PHI)
4. PaymentIntent created with status INITIALIZED
5. Authorization URL returned to frontend

#### 2. Verify Payment Intent
**POST** `/api/v1/visits/{visit_id}/payment-intents/{id}/verify/`

**Authentication**: Receptionist only  
**Request Body**:
```json
{
  "reference": "VISIT-123-ABC123"
}
```

**Response**:
```json
{
  "message": "Payment verified successfully.",
  "payment_intent": {...},
  "payment_id": 456
}
```

**Flow**:
1. Receptionist triggers verification (or automatic after payment)
2. **Server-side Paystack verification** (CRITICAL: frontend NOT trusted)
3. Transaction status checked
4. Visit ID verified in Paystack metadata (security check)
5. PaymentIntent marked as VERIFIED
6. Payment record created (status: CLEARED)
7. Visit payment_status updated to CLEARED

**Idempotency**: Can be called multiple times safely - returns existing payment if already verified

#### 3. Paystack Webhook
**POST** `/api/v1/billing/paystack/webhook/`

**Authentication**: None (public endpoint, signature-verified)  
**Headers**:
- `X-Paystack-Signature`: Webhook signature (required)

**Flow**:
1. Paystack sends webhook after payment
2. **Webhook signature verified** (HMAC SHA512)
3. Event type checked (only `charge.success` processed)
4. PaymentIntent found by reference
5. **Idempotency check**: If already verified, return success
6. **Server-side verification** (do not trust webhook data alone)
7. Transaction status checked
8. Visit ID verified in metadata
9. PaymentIntent marked as VERIFIED
10. Payment record created
11. Audit log created

**Security**:
- Signature validation prevents tampering
- Server-side verification prevents frontend manipulation
- Idempotency prevents duplicate processing
- Visit ID verification ensures visit-scoped integrity

## Metadata Structure (NO PHI)

Paystack metadata contains ONLY system identifiers:
```json
{
  "visit_id": 123,              // System identifier only
  "reference": "VISIT-123-...", // System reference
  "source": "emr_visit_billing" // System identifier
}
```

**DO NOT INCLUDE**:
- Patient name
- Patient email (unless generic payment email)
- Medical records
- Diagnosis
- Any PHI

## Payment Flow

```
1. Receptionist → Initialize Payment Intent
   ↓
2. System → Generate Paystack Reference
   ↓
3. System → Initialize Paystack Transaction (NO PHI)
   ↓
4. Frontend → Redirect to Paystack Checkout
   ↓
5. Patient → Complete Payment on Paystack
   ↓
6. Paystack → Send Webhook (signature-verified)
   ↓
7. System → Verify Transaction Server-Side
   ↓
8. System → Create Payment Record
   ↓
9. System → Update Visit.payment_status = CLEARED
```

## Error Handling

### Initialization Failures
- Paystack API errors returned to client
- PaymentIntent not created if initialization fails

### Verification Failures
- PaymentIntent marked as FAILED
- Error message returned to client
- Payment record NOT created

### Webhook Failures
- Invalid signature → 401 Unauthorized
- Missing reference → 404 Not Found
- Verification failure → PaymentIntent marked as FAILED
- All errors logged for audit

## Audit Logging

All actions are logged to AuditLog:
- `PAYSTACK_PAYMENT_INITIALIZED`: Payment intent created
- `PAYSTACK_PAYMENT_VERIFIED`: Payment verified (manual)
- `PAYSTACK_WEBHOOK_PROCESSED`: Webhook processed (automatic)

## Testing

### Manual Testing
1. Create a Visit
2. Initialize payment intent (Receptionist)
3. Complete payment on Paystack (test mode)
4. Verify payment (or wait for webhook)
5. Check Payment record created
6. Check Visit.payment_status = CLEARED

### Webhook Testing
Use Paystack webhook testing tool or ngrok for local testing:
```bash
ngrok http 8000
# Configure Paystack webhook URL: https://your-ngrok-url/api/v1/billing/paystack/webhook/
```

## Configuration

Required environment variables:
```env
PAYSTACK_SECRET_KEY=sk_test_...
PAYSTACK_PUBLIC_KEY=pk_test_...
PAYSTACK_CALLBACK_URL=https://your-domain.com/callback
```

## Compliance Checklist

✅ **Visit-Scoped**: All transactions mapped to Visit  
✅ **No PHI**: Only system identifiers in Paystack metadata  
✅ **Server-Side Verification**: All verification server-side  
✅ **Webhook Security**: Signature validation required  
✅ **Idempotency**: Safe to retry operations  
✅ **Immutable Records**: Payment records immutable after creation  
✅ **Audit Logging**: All actions logged  
✅ **Receptionist-Only**: Only Receptionists can initialize payments  

## Rejected Patterns

❌ **Frontend Verification**: Never trust frontend verification  
❌ **PHI in Metadata**: Never send patient data to Paystack  
❌ **Skip Webhook Validation**: Always verify webhook signatures  
❌ **Modify Verified Payments**: Payment records are immutable  
❌ **Non-Visit-Scoped**: All payments must be visit-scoped  

## Future Enhancements

1. **Refund Support**: Add refund processing for Paystack payments
2. **Partial Payments**: Support partial payment intents
3. **Payment Status Polling**: Automatic status polling for pending payments
4. **Payment History**: Enhanced payment history view
5. **Multi-Gateway Support**: Extend to other payment gateways


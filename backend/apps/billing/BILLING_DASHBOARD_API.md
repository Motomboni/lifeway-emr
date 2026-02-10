# Receptionist Billing Dashboard API

## Overview

This document describes the Receptionist Billing Dashboard API endpoint that provides comprehensive, real-time billing information for a visit.

## Endpoint

**GET** `/api/v1/billing/visit/{visit_id}/summary/`

### Authentication
- Requires authentication
- Requires `CanProcessPayment` permission (Receptionist role)

### Query Parameters
- `insurance_view`: `true`/`false` (default: `false`) - Enable insurance-specific view mode

## Response Structure

### Standard Response

```json
{
    "visit_id": 1,
    "visit_status": "OPEN",
    "visit_type": "CONSULTATION",
    "chief_complaint": "Headache",
    "created_at": "2024-01-15T10:00:00Z",
    
    "patient": {
        "id": 1,
        "patient_id": "LMC000001",
        "full_name": "John Doe",
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone": "+2348012345678",
        "date_of_birth": "1990-01-01",
        "gender": "MALE"
    },
    
    "bill": {
        "id": 1,
        "is_insurance_backed": false,
        "total_amount": "15000.00",
        "amount_paid": "5000.00",
        "outstanding_balance": "10000.00",
        "status": "PARTIALLY_PAID"
    },
    
    "items_by_department": [
        {
            "department": "LAB",
            "items": [
                {
                    "id": 1,
                    "service_name": "Complete Blood Count",
                    "amount": "5000.00",
                    "status": "UNPAID",
                    "created_at": "2024-01-15T10:30:00Z"
                },
                {
                    "id": 2,
                    "service_name": "Blood Sugar Test",
                    "amount": "3000.00",
                    "status": "UNPAID",
                    "created_at": "2024-01-15T10:35:00Z"
                }
            ],
            "item_count": 2,
            "total_amount": "8000.00"
        },
        {
            "department": "PHARMACY",
            "items": [
                {
                    "id": 3,
                    "service_name": "Paracetamol 500mg x 20",
                    "amount": "2000.00",
                    "status": "UNPAID",
                    "created_at": "2024-01-15T11:00:00Z"
                }
            ],
            "item_count": 1,
            "total_amount": "2000.00"
        },
        {
            "department": "RADIOLOGY",
            "items": [
                {
                    "id": 4,
                    "service_name": "Chest X-Ray",
                    "amount": "5000.00",
                    "status": "UNPAID",
                    "created_at": "2024-01-15T11:15:00Z"
                }
            ],
            "item_count": 1,
            "total_amount": "5000.00"
        }
    ],
    "total_items": 4,
    
    "payment_history": [
        {
            "id": 1,
            "amount": "5000.00",
            "payment_method": "POS",
            "transaction_reference": "POS-123456",
            "notes": "Payment via POS terminal",
            "processed_by": "Receptionist Name",
            "created_at": "2024-01-15T12:00:00Z"
        }
    ],
    "payment_count": 1,
    
    "insurance": null,
    "insurance_coverage": null,
    "patient_payable_after_insurance": null,
    
    "summary": {
        "total_bill": "15000.00",
        "total_paid": "5000.00",
        "outstanding_balance": "10000.00",
        "payment_status": "PARTIALLY_PAID",
        "can_accept_payment": true,
        "is_fully_paid": false,
        "is_partially_paid": true
    }
}
```

### Insurance View Response

When `insurance_view=true` and bill is insurance-backed:

```json
{
    // ... all standard fields ...
    
    "bill": {
        "id": 1,
        "is_insurance_backed": true,
        "total_amount": "20000.00",
        "amount_paid": "0.00",
        "outstanding_balance": "20000.00",
        "status": "INSURANCE_PENDING"
    },
    
    "insurance": {
        "provider_name": "Health Insurance Co.",
        "provider_code": "HIC001",
        "policy_number": "POL-123456",
        "coverage_type": "FULL",
        "coverage_percentage": "100.00",
        "is_valid": true,
        "valid_from": "2024-01-01",
        "valid_to": "2024-12-31"
    },
    
    "insurance_coverage": "20000.00",
    "patient_payable_after_insurance": "0.00",
    
    "insurance_view": {
        "insurance_amount": "20000.00",
        "patient_payable": "0.00",
        "patient_paid": "0.00",
        "patient_outstanding": "0.00",
        "insurance_status": "COVERED"
    },
    
    "summary": {
        "total_bill": "20000.00",
        "total_paid": "0.00",
        "outstanding_balance": "20000.00",
        "payment_status": "INSURANCE_PENDING",
        "can_accept_payment": false,
        "is_fully_paid": false,
        "is_partially_paid": false
    }
}
```

## Features

### 1. Real-Time Accurate Totals

- Totals are recalculated on every request
- Uses `bill.recalculate_totals()` to ensure accuracy
- Reflects latest bill items and payments

### 2. Bill Items Grouped by Department

- Items are grouped by department (LAB, PHARMACY, RADIOLOGY, PROCEDURE)
- Each department shows:
  - List of items
  - Item count
  - Department total amount

### 3. Payment History

- Complete payment history with:
  - Payment amount
  - Payment method
  - Transaction reference
  - Notes
  - Processed by (Receptionist name)
  - Timestamp

### 4. Partial Payment Support

- `is_partially_paid`: Indicates if partial payment has been made
- `outstanding_balance`: Shows remaining amount to be paid
- `can_accept_payment`: Indicates if more payments can be accepted

### 5. Insurance View Mode

When `insurance_view=true`:
- Shows insurance-specific calculations
- Displays insurance coverage amount
- Shows patient payable after insurance
- Indicates insurance status (COVERED, PARTIAL, PENDING)

## Response Fields

### Patient Details
- `id`: Patient ID
- `patient_id`: Patient identifier
- `full_name`: Full name
- `first_name`: First name
- `last_name`: Last name
- `email`: Email address
- `phone`: Phone number
- `date_of_birth`: Date of birth
- `gender`: Gender

### Bill Information
- `id`: Bill ID
- `is_insurance_backed`: Whether bill is insurance-backed
- `total_amount`: Total bill amount
- `amount_paid`: Total amount paid
- `outstanding_balance`: Outstanding balance
- `status`: Payment status (UNPAID, PARTIALLY_PAID, PAID, INSURANCE_PENDING, INSURANCE_CLAIMED, SETTLED)

### Items by Department
- `department`: Department name
- `items`: List of bill items
- `item_count`: Number of items in department
- `total_amount`: Department total

### Payment History
- `id`: Payment ID
- `amount`: Payment amount
- `payment_method`: Payment method (CASH, POS, TRANSFER, PAYSTACK, WALLET, INSURANCE)
- `transaction_reference`: Transaction reference
- `notes`: Payment notes
- `processed_by`: Receptionist who processed payment
- `created_at`: Payment timestamp

### Insurance Information
- `provider_name`: Insurance provider name
- `provider_code`: Provider code
- `policy_number`: Policy number
- `coverage_type`: FULL or PARTIAL
- `coverage_percentage`: Coverage percentage (0-100)
- `is_valid`: Whether policy is currently valid
- `valid_from`: Policy start date
- `valid_to`: Policy end date

### Summary
- `total_bill`: Total bill amount
- `total_paid`: Total amount paid
- `outstanding_balance`: Outstanding balance
- `payment_status`: Payment status
- `can_accept_payment`: Whether more payments can be accepted
- `is_fully_paid`: Whether bill is fully paid
- `is_partially_paid`: Whether partial payment has been made

## Error Responses

### 404 Not Found
```json
{
    "detail": "Visit with id 999 not found."
}
```

### 403 Forbidden
```json
{
    "detail": "You do not have permission to perform this action."
}
```

## Usage Examples

### Get Standard Billing Summary

```bash
GET /api/v1/billing/visit/1/summary/
Authorization: Bearer <token>
```

### Get Insurance View

```bash
GET /api/v1/billing/visit/1/summary/?insurance_view=true
Authorization: Bearer <token>
```

## Integration Notes

1. **Real-Time Updates**: Totals are recalculated on every request, ensuring accuracy
2. **Department Grouping**: Items are automatically grouped by department for easy viewing
3. **Payment Tracking**: Complete payment history is included for audit purposes
4. **Insurance Support**: Insurance view mode provides insurance-specific calculations
5. **Partial Payments**: System fully supports partial payments with accurate tracking

## Performance Considerations

- Totals are recalculated on every request (ensures accuracy)
- Database queries are optimized with proper indexing
- Response includes all necessary information in a single request
- Consider caching for high-traffic scenarios (with cache invalidation on updates)

## Security

- Requires authentication
- Requires Receptionist permission (`CanProcessPayment`)
- All actions are logged to AuditLog
- Visit access is validated


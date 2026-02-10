# Retainership Integration

## Overview

Retainership functionality has been fully integrated into the EMR billing system. Patients with active retainership agreements receive automatic discounts on all charges.

## Features Implemented

### 1. Retainership Utilities (`retainership_utils.py`)

- **`is_retainership_active(patient, check_date)`**: Checks if patient has an active retainership
  - Validates `has_retainership` flag
  - Checks start date has passed
  - Checks end date hasn't passed (if exists)

- **`get_retainership_discount_percentage(patient)`**: Gets discount percentage based on retainership type
  - Monthly: 10%
  - Quarterly: 15%
  - Annual: 20%
  - Corporate: 25%
  - Default: 10% (for unknown types)

- **`compute_retainership_discount(total_charges, patient)`**: Calculates discount amount
  - Applies percentage discount to total charges
  - Returns discount amount in Naira

- **`get_retainership_info(patient)`**: Returns comprehensive retainership information
  - Active status
  - Discount percentage
  - Days until expiry
  - Expiry status

### 2. Billing Service Integration

The `BillingService` now:
- Checks for active retainership on visit patient
- Applies retainership discount to total charges
- Calculates charges after retainership discount
- Applies insurance coverage to charges after retainership (not before)
- Includes retainership information in `BillingSummary`

**Discount Application Order:**
1. Calculate total charges
2. Apply retainership discount → `charges_after_retainership`
3. Apply insurance coverage to `charges_after_retainership`
4. Calculate patient payable

### 3. BillingSummary Updates

`BillingSummary` dataclass now includes:
- `has_retainership`: bool
- `retainership_discount`: Decimal (discount amount)
- `retainership_discount_percentage`: Decimal (discount %)
- `charges_after_retainership`: Decimal (charges after discount)

### 4. Visit Serializer Updates

`VisitReadSerializer` now includes:
- `patient_retainership`: Dict with retainership information
  - `has_retainership`
  - `is_active`
  - `retainership_type`
  - `retainership_start_date`
  - `retainership_end_date`
  - `retainership_amount`
  - `discount_percentage`
  - `days_until_expiry`
  - `is_expired`

### 5. Frontend Integration

- **BillingSummary Component**: Displays retainership discount card
  - Shows discount amount
  - Shows discount percentage
  - Orange-themed card for visibility

- **BillingSummary Type**: Updated to include retainership fields

- **CSS Styles**: Added orange theme for retainership discount card

## Retainership Discount Rules

### Discount Percentages by Type

| Retainership Type | Discount |
|------------------|----------|
| Monthly | 10% |
| Quarterly | 15% |
| Annual | 20% |
| Corporate | 25% |
| Other/Unknown | 10% (default) |

### Active Retainership Criteria

A retainership is considered active if:
1. `has_retainership` is `True`
2. `retainership_start_date` exists and is <= today
3. If `retainership_end_date` exists, it must be >= today

### Discount Application

- Discount is applied to **total charges** before insurance calculations
- Discount is calculated as: `total_charges * (discount_percentage / 100)`
- Discount is rounded to 2 decimal places
- If retainership is not active, discount is `0.00`

## Billing Flow with Retainership

```
1. Total Charges Calculated
   ↓
2. Retainership Discount Applied (if active)
   → charges_after_retainership = total_charges - retainership_discount
   ↓
3. Insurance Coverage Calculated (on charges_after_retainership)
   → insurance_amount = compute_insurance_coverage(charges_after_retainership)
   ↓
4. Patient Payable Calculated
   → patient_payable = charges_after_retainership - insurance_amount
   ↓
5. Outstanding Balance Calculated
   → outstanding_balance = patient_payable - (payments + wallet_debits)
```

## Example Calculation

**Scenario:**
- Total Charges: ₦10,000.00
- Retainership: Annual (20% discount)
- Insurance: None

**Calculation:**
1. Retainership Discount: ₦10,000.00 × 20% = ₦2,000.00
2. Charges After Retainership: ₦10,000.00 - ₦2,000.00 = ₦8,000.00
3. Patient Payable: ₦8,000.00 (no insurance)
4. Outstanding Balance: ₦8,000.00 - payments

## API Response Example

```json
{
  "total_charges": "10000.00",
  "has_retainership": true,
  "retainership_discount": "2000.00",
  "retainership_discount_percentage": "20.00",
  "charges_after_retainership": "8000.00",
  "has_insurance": false,
  "insurance_amount": "0.00",
  "patient_payable": "8000.00",
  "outstanding_balance": "8000.00",
  "payment_status": "UNPAID"
}
```

## Frontend Display

The billing summary displays:
- **Total Charges**: Original charges before discount
- **Retainership Discount** (if active): Discount amount and percentage
- **Charges After Retainership**: Charges after discount (used for insurance and patient payable)
- **Insurance Coverage**: Insurance amount (if applicable)
- **Patient Payable**: Final amount patient must pay

## Testing

To test retainership integration:

1. **Create Patient with Retainership:**
   - Register patient with `has_retainership=True`
   - Set `retainership_type` (e.g., "ANNUAL")
   - Set `retainership_start_date` (today or past)
   - Set `retainership_amount` (optional)

2. **Create Visit:**
   - Create visit for patient with retainership
   - Add charges to visit

3. **Verify Billing:**
   - Check billing summary shows retainership discount
   - Verify discount percentage matches retainership type
   - Verify charges after retainership are correct
   - Verify patient payable is calculated correctly

4. **Test Expiry:**
   - Set `retainership_end_date` to past date
   - Verify discount is not applied
   - Verify `is_active` is `False`

## Future Enhancements

Potential future enhancements:
- Retainership expiry notifications
- Retainership renewal workflow
- Retainership usage tracking
- Custom discount percentages per retainership
- Retainership-specific service pricing


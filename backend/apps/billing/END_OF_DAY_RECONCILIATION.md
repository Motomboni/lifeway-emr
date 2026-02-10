# End-of-Day Reconciliation

## Overview

The End-of-Day Reconciliation feature provides a comprehensive daily reconciliation process for clinic operations. It automatically closes active visits, reconciles all payment methods, detects revenue leaks, and generates a detailed summary report.

## Key Features

- **Automatic Visit Closure**: Closes all ACTIVE visits for the day
- **Payment Reconciliation**: Reconciles Cash, Wallet, Paystack, HMO, and Insurance payments
- **Revenue Leak Detection**: Automatically detects revenue leaks
- **Outstanding Balance Tracking**: Identifies unpaid services
- **Staff Sign-off**: Tracks who prepared, reviewed, and finalized the reconciliation
- **Idempotent**: Safe to run multiple times (one report per day)
- **Immutable**: Cannot be edited once finalized (except notes)

## Process Flow

1. **Trigger**: Admin or Receptionist initiates reconciliation
2. **Close Visits**: All ACTIVE visits for the day are closed
3. **Calculate Totals**: Sum all payments by method
4. **Detect Leaks**: Run revenue leak detection
5. **Calculate Outstanding**: Sum all unpaid/partially paid bills
6. **Generate Report**: Create detailed reconciliation record
7. **Finalize**: Staff reviews and finalizes (immutable after this)

## Models

### EndOfDayReconciliation

Tracks daily reconciliation with:
- `reconciliation_date`: Date of reconciliation (unique, one per day)
- `status`: DRAFT, FINALIZED, or CANCELLED
- Revenue totals by payment method
- Outstanding balances
- Revenue leaks detected
- Visit statistics
- Staff sign-off (prepared_by, reviewed_by, finalized_by)
- Detailed breakdown (JSON)

## API Endpoints

### Create Reconciliation
```
POST /api/v1/billing/reconciliation/
```

Request:
```json
{
  "reconciliation_date": "2026-01-15",
  "close_active_visits": true
}
```

### Get Reconciliation
```
GET /api/v1/billing/reconciliation/{id}/
```

### Finalize Reconciliation
```
POST /api/v1/billing/reconciliation/{id}/finalize/
```

Request:
```json
{
  "notes": "All payments verified"
}
```

### Refresh Reconciliation
```
POST /api/v1/billing/reconciliation/{id}/refresh/
```

Re-calculates all totals and statistics.

### Get Today's Reconciliation
```
GET /api/v1/billing/reconciliation/today/
```

### Get Summary
```
GET /api/v1/billing/reconciliation/summary/?start_date=2026-01-01&end_date=2026-01-31
```

## Service Layer

### ReconciliationService

Provides methods for:
- `create_reconciliation()`: Create new reconciliation
- `refresh_reconciliation()`: Refresh calculations
- `get_reconciliation_for_date()`: Get reconciliation for specific date
- `get_reconciliation_summary()`: Get summary of reconciliation

## Constraints

### One Report Per Day
- Only one reconciliation can exist per day
- Creating a second reconciliation for the same day returns the existing one
- Enforced by unique constraint on `reconciliation_date`

### Immutability
- Once finalized, reconciliation cannot be edited (except notes)
- Validated in model's `clean()` method
- Prevents accidental modification of finalized records

### Idempotency
- Safe to run reconciliation multiple times
- Returns existing reconciliation if already exists
- Refresh updates calculations without creating duplicates

## Reconciliation Details

The reconciliation includes:

### Revenue Totals
- Total revenue
- Cash payments
- Wallet payments
- Paystack payments
- HMO payments
- Insurance payments

### Outstanding Balances
- Total outstanding amount
- Number of visits with outstanding balances

### Revenue Leaks
- Number of leaks detected
- Total amount of leaks

### Visit Statistics
- Total visits for the day
- Number of active visits closed

### Mismatches
- Flag for payment mismatches
- Details of mismatches (JSON)

## Staff Sign-off

Tracks:
- `prepared_by`: User who created the reconciliation
- `prepared_at`: When reconciliation was created
- `reviewed_by`: User who reviewed (optional)
- `reviewed_at`: When reviewed (optional)
- `finalized_by`: User who finalized
- `finalized_at`: When finalized

## Usage Example

```python
from apps.billing.reconciliation_service import ReconciliationService
from django.utils import timezone

# Create reconciliation for today
reconciliation = ReconciliationService.create_reconciliation(
    reconciliation_date=timezone.now().date(),
    prepared_by_id=user.id,
    close_active_visits=True
)

# Review the reconciliation
print(f"Total Revenue: {reconciliation.total_revenue}")
print(f"Cash: {reconciliation.total_cash}")
print(f"Outstanding: {reconciliation.total_outstanding}")
print(f"Revenue Leaks: {reconciliation.revenue_leaks_detected}")

# Finalize
reconciliation.finalize(user)
```

## Admin Interface

The Django admin provides:
- List view with filters (date, status, mismatches)
- Read-only fields for finalized reconciliations
- Notes can be edited even after finalization
- Search by date, notes, staff names

## Testing

Run tests:
```bash
python manage.py test apps.billing.tests_reconciliation
```

Test coverage:
- Creating reconciliation
- One reconciliation per day constraint
- Reconciliation with visits and payments
- Finalizing reconciliation
- Immutability after finalization
- Idempotency
- Refresh functionality

## Best Practices

1. **Run Daily**: Run reconciliation at end of each business day
2. **Review Before Finalizing**: Always review totals before finalizing
3. **Check Leaks**: Review revenue leaks and resolve them
4. **Verify Totals**: Ensure payment method totals match physical records
5. **Add Notes**: Document any discrepancies or special circumstances
6. **Finalize Promptly**: Finalize once verified to prevent accidental changes

## Future Enhancements

Potential enhancements:
- Email notifications on completion
- PDF report generation
- Comparison with previous days
- Automated reconciliation scheduling
- Integration with accounting systems
- Cash drawer reconciliation
- Payment method breakdown charts


# Revenue Leak Detection Module

## Overview

The Revenue Leak Detection module identifies cases where clinical actions are completed without corresponding paid BillingLineItems. This helps prevent revenue loss by ensuring all services are properly billed and paid.

## Definition

A **revenue leak** occurs when a clinical action is completed without a corresponding paid BillingLineItem.

## Detected Cases

1. **LabResult exists but no PAID bill** for its ServiceCatalog
2. **RadiologyReport exists but no PAID bill**
3. **DrugDispense exists but no PAID bill** (emergency overrides excluded)
4. **Procedure marked completed but unpaid**

## Architecture

### Models

#### LeakRecord

Tracks detected revenue leaks with the following fields:

- `entity_type`: Type of entity (LAB_RESULT, RADIOLOGY_REPORT, DRUG_DISPENSE, PROCEDURE)
- `entity_id`: ID of the entity that triggered the leak
- `service_code`: Service code from ServiceCatalog
- `service_name`: Service name from ServiceCatalog
- `estimated_amount`: Estimated revenue loss
- `visit`: Visit where the leak was detected
- `detected_at`: When the leak was first detected
- `resolved_at`: When the leak was resolved (nullable)
- `resolved_by`: User who resolved the leak (nullable)
- `resolution_notes`: Notes about resolution
- `detection_context`: Additional context (JSON)

### Service Layer

#### LeakDetectionService

Provides methods for detecting leaks:

- `detect_lab_result_leak(lab_result_id)`: Detect leaks for LabResult
- `detect_radiology_report_leak(radiology_request_id)`: Detect leaks for RadiologyRequest
- `detect_drug_dispense_leak(prescription_id)`: Detect leaks for Prescription
- `detect_procedure_leak(procedure_task_id)`: Detect leaks for ProcedureTask
- `detect_all_leaks()`: Scan all entities and detect leaks
- `get_daily_aggregation(date)`: Get daily aggregation of leaks

### API Endpoints

**Base URL:** `/api/v1/billing/leaks/`

All endpoints require admin authentication.

#### List Leaks

```
GET /api/v1/billing/leaks/
```

Query parameters:
- `resolved`: Filter by resolved status (true/false)
- `entity_type`: Filter by entity type
- `visit_id`: Filter by visit
- `date_from`: Filter by date range (start)
- `date_to`: Filter by date range (end)

#### Get Leak Details

```
GET /api/v1/billing/leaks/{id}/
```

#### Resolve Leak

```
POST /api/v1/billing/leaks/{id}/resolve/
```

Request body:
```json
{
  "resolution_notes": "Bill was created and paid"
}
```

#### Detect All Leaks

```
POST /api/v1/billing/leaks/detect_all/
```

Runs leak detection for all entities in the system.

#### Daily Aggregation

```
GET /api/v1/billing/leaks/daily_aggregation/?date=2026-01-10
```

Returns daily aggregation of leaks.

#### Summary Statistics

```
GET /api/v1/billing/leaks/summary/
```

Returns summary statistics of leaks.

### Management Command

Run leak detection manually:

```bash
python manage.py detect_revenue_leaks
```

## Key Features

### Idempotent Detection

Leak detection is idempotent - detecting the same leak multiple times returns the same LeakRecord. This is enforced by a unique constraint on `(entity_type, entity_id)` for unresolved leaks.

### Emergency Override Exclusion

Emergency prescriptions (`is_emergency=True`) are excluded from leak detection, as they are allowed to be dispensed without payment clearance.

### Manual Resolution Only

Leaks must be reviewed and resolved manually. There is no auto-fix functionality. This ensures proper audit trail and prevents accidental revenue adjustments.

### Daily Aggregation

The system provides daily aggregation functions to track:
- Total leaks detected
- Total estimated revenue loss
- Resolved vs unresolved leaks
- Breakdown by entity type

## Usage Examples

### Detect Leaks for All Entities

```python
from apps.billing.leak_detection_service import LeakDetectionService

results = LeakDetectionService.detect_all_leaks()
print(f"Total leaks: {results['total_leaks']}")
print(f"Estimated loss: {results['total_estimated_loss']} NGN")
```

### Get Daily Aggregation

```python
from datetime import date
from apps.billing.leak_detection_service import LeakDetectionService

aggregation = LeakDetectionService.get_daily_aggregation(date(2026, 1, 10))
print(f"Leaks on {aggregation['date']}: {aggregation['total_leaks']}")
print(f"Unresolved: {aggregation['unresolved']['count']}")
```

### Resolve a Leak

```python
from apps.billing.leak_detection_models import LeakRecord

leak = LeakRecord.objects.get(id=1)
leak.resolve(
    user=request.user,
    notes="Bill was created and paid"
)
```

## Testing

Unit tests are provided in `tests_leak_detection.py` covering:

- LabResult leak detection
- RadiologyReport leak detection
- DrugDispense leak detection
- Procedure leak detection
- Idempotent detection
- Emergency override exclusion
- Leak resolution
- Daily aggregation

Run tests:

```bash
python manage.py test apps.billing.tests_leak_detection
```

## Admin Interface

LeakRecord is registered in Django admin with:

- List view with filters
- Read-only fields for audit compliance
- Bulk action to mark leaks as resolved
- Search functionality
- Date hierarchy

## Compliance

- **Idempotent detection**: Same leak = same record
- **Manual resolution only**: No auto-fix
- **Emergency exclusion**: Emergency overrides excluded
- **Audit trail**: All resolutions tracked with user and timestamp
- **Immutable records**: Leaks cannot be deleted (audit compliance)

## Future Enhancements

- Scheduled daily leak detection (Celery task)
- Email notifications for unresolved leaks
- Dashboard visualization
- Leak trend analysis
- Integration with billing reconciliation


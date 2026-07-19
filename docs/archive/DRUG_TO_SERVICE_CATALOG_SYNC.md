# Drug to Service Catalog Auto-Sync Feature

## Overview

This feature automatically creates and maintains Service Catalog entries for all drugs in the Drug Catalog Management system. When a drug is created, updated, or deleted, the corresponding Service Catalog entry is automatically synchronized.

## Implementation Details

### Files Created/Modified

1. **`backend/apps/pharmacy/signals.py`** (NEW)
   - Contains Django signal handlers for Drug model
   - Automatically creates/updates ServiceCatalog entries when drugs are created/updated
   - Deactivates ServiceCatalog entries when drugs are deleted

2. **`backend/apps/pharmacy/apps.py`** (NEW)
   - App configuration file that registers the signals module
   - Ensures signals are loaded when the app starts

3. **`backend/core/settings.py`** (MODIFIED)
   - Updated `INSTALLED_APPS` to use `apps.pharmacy.apps.PharmacyConfig` instead of `apps.pharmacy`
   - This ensures the signals are properly registered

## How It Works

### When a Drug is Created

1. A `post_save` signal is triggered
2. The signal handler checks if a ServiceCatalog entry already exists for this drug (by name or service code)
3. If no entry exists, a new ServiceCatalog entry is created with:
   - **Department**: `PHARMACY`
   - **Service Code**: `DRUG-{drug_code}` or `DRUG-{drug_id}` if no drug_code
   - **Name**: Drug name
   - **Amount**: Drug sales_price (or cost_price if sales_price not available)
   - **Category**: `DRUG`
   - **Workflow Type**: `DRUG_DISPENSE`
   - **Requires Visit**: `True`
   - **Requires Consultation**: `True` (drugs require consultation)
   - **Auto Bill**: `True`
   - **Bill Timing**: `AFTER` (bill after dispensing)
   - **Allowed Roles**: `['DOCTOR', 'NURSE']` (default)
   - **Is Active**: Matches drug's `is_active` status
   - **Description**: Combines generic_name, drug_class, dosage_forms, common_dosages, and description

### When a Drug is Updated

1. A `post_save` signal is triggered
2. The signal handler finds the existing ServiceCatalog entry (by name or service code)
3. The ServiceCatalog entry is updated with:
   - Name
   - Amount (sales_price or cost_price)
   - Description
   - Is Active status
   - Service Code (if drug_code changed and new code is available)

### When a Drug is Deleted

1. A `post_delete` signal is triggered
2. The signal handler finds matching ServiceCatalog entries
3. Instead of deleting them (which would break billing history), they are **deactivated** (`is_active = False`)

## Service Code Generation

The service code is generated using the following priority:

1. **If drug_code exists**: `DRUG-{drug_code}` (uppercase)
2. **If drug has ID**: `DRUG-{drug_id:06d}` (zero-padded 6 digits)
3. **Fallback**: `DRUG-{sanitized_drug_name}` (for new drugs without ID yet)

If a service code already exists, a counter is appended: `DRUG-{code}-1`, `DRUG-{code}-2`, etc.

## Error Handling

- All signal handlers are wrapped in try/except blocks
- Errors are logged but don't prevent drug creation/update/deletion
- This ensures the drug management workflow is not disrupted if ServiceCatalog sync fails

## Benefits

1. **Automatic Synchronization**: No manual work required to add drugs to Service Catalog
2. **Consistency**: Drug information in Service Catalog always matches Drug Catalog
3. **Billing Integration**: Drugs automatically appear in billing/service ordering interfaces
4. **Workflow Integration**: Drugs automatically trigger the `DRUG_DISPENSE` workflow when ordered
5. **Data Integrity**: Deleted drugs are deactivated (not deleted) to preserve billing history

## Usage

### Creating a Drug

Simply create a drug through the Drug Catalog Management interface. The Service Catalog entry will be created automatically:

```python
from apps.pharmacy.models import Drug
from apps.users.models import User

drug = Drug.objects.create(
    name="Paracetamol 500mg",
    drug_code="PAR-500",
    sales_price=50.00,
    description="Pain reliever",
    created_by=pharmacist_user
)
# ServiceCatalog entry is automatically created!
```

### Updating a Drug

Update the drug normally, and the Service Catalog entry will be updated automatically:

```python
drug.sales_price = 60.00
drug.is_active = False
drug.save()
# ServiceCatalog entry is automatically updated!
```

### Viewing Service Catalog Entries

Drugs will appear in the Service Catalog with department `PHARMACY`:

```python
from apps.billing.service_catalog_models import ServiceCatalog

pharmacy_services = ServiceCatalog.objects.filter(
    department='PHARMACY',
    category='DRUG',
    is_active=True
)
```

## Testing

To test the feature:

1. Create a new drug in the Drug Catalog Management interface
2. Check the Service Catalog - the drug should appear automatically
3. Update the drug's price or status
4. Verify the Service Catalog entry is updated
5. Delete a drug
6. Verify the Service Catalog entry is deactivated (not deleted)

## Notes

- The signal handlers skip raw saves (e.g., during migrations) to prevent issues during database migrations
- Service codes are automatically made unique if duplicates exist
- The feature is backward compatible - existing drugs without Service Catalog entries will get them created on their next update

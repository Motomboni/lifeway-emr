# Service Catalog Import Guide

This guide explains how to import services into the ServiceCatalog using the `import_service_catalog` management command.

## Supported File Formats

- **CSV** (`.csv`): Comma-separated values
- **Excel** (`.xlsx`, `.xls`): Microsoft Excel files
- **JSON** (`.json`): JavaScript Object Notation

## Command Usage

```bash
# Import from CSV
python manage.py import_service_catalog services.csv

# Import from Excel
python manage.py import_service_catalog services.xlsx

# Import from JSON
python manage.py import_service_catalog services.json

# Dry run (test without saving)
python manage.py import_service_catalog services.csv --dry-run

# Update existing services
python manage.py import_service_catalog services.csv --update

# Specify Excel sheet
python manage.py import_service_catalog services.xlsx --sheet "Sheet1"
```

## Required Fields

| Field | Description | Valid Values |
|-------|-------------|--------------|
| **Department** | Department providing the service | `CONSULTATION`, `LAB`, `PHARMACY`, `RADIOLOGY`, `PROCEDURE` |
| **Service Code** | Unique identifier | Any string (e.g., "CONS-001", "CBC-001") |
| **Service Name** | Display name | Any string |
| **Amount** | Price in Naira | Numeric value > 0 |

## Optional Fields (with defaults)

| Field | Description | Default | Valid Values |
|-------|-------------|---------|--------------|
| **Description** | Detailed description | Empty string | Any text |
| **Category** | Service category | Inferred from department | `CONSULTATION`, `LAB`, `DRUG`, `PROCEDURE`, `RADIOLOGY` |
| **Workflow Type** | Workflow triggered | Inferred from department | `GOPD_CONSULT`, `LAB_ORDER`, `DRUG_DISPENSE`, `PROCEDURE`, `RADIOLOGY_STUDY`, `INJECTION`, `DRESSING`, `VACCINATION`, `PHYSIOTHERAPY`, `OTHER` |
| **Requires Visit** | Needs active visit | `TRUE` | `TRUE`, `FALSE` |
| **Requires Consultation** | Needs consultation | `FALSE` | `TRUE`, `FALSE` |
| **Auto Bill** | Auto-create bill | `TRUE` | `TRUE`, `FALSE` |
| **Bill Timing** | When to bill | `AFTER` | `BEFORE`, `AFTER` |
| **Allowed Roles** | Who can order | `DOCTOR` | Comma-separated: `DOCTOR`, `NURSE`, `LAB_TECH`, `RADIOLOGY_TECH`, `PHARMACIST`, `RECEPTIONIST`, `ADMIN`, `PATIENT` |
| **Is Active** | Service is active | `TRUE` | `TRUE`, `FALSE` |

## Field Name Variations

The import command accepts various field name formats (case-insensitive):

- **Department**: `department`, `dept`
- **Service Code**: `service code`, `service_code`, `code`
- **Service Name**: `service name`, `name`, `service_name`
- **Amount**: `amount`, `price`, `cost`
- **Description**: `description`, `desc`
- **Category**: `category`, `cat`
- **Workflow Type**: `workflow type`, `workflow_type`, `workflow`
- **Requires Visit**: `requires visit`, `requires_visit`, `needs visit`
- **Requires Consultation**: `requires consultation`, `requires_consultation`, `needs consultation`
- **Auto Bill**: `auto bill`, `auto_bill`, `auto bill`
- **Bill Timing**: `bill timing`, `bill_timing`, `billing timing`
- **Allowed Roles**: `allowed roles`, `allowed_roles`, `roles`
- **Is Active**: `is active`, `is_active`, `active`

## CSV Format Example

```csv
Department,Service Code,Service Name,Amount,Description,Category,Workflow Type,Requires Visit,Requires Consultation,Auto Bill,Bill Timing,Allowed Roles,Is Active
CONSULTATION,GOPD-CONSULT,General Consultation,5000.00,Standard consultation,CONSULTATION,GOPD_CONSULT,TRUE,FALSE,TRUE,BEFORE,DOCTOR,TRUE
LAB,LAB-CBC,Complete Blood Count,2500.00,Full blood count,LAB,LAB_ORDER,TRUE,TRUE,TRUE,BEFORE,DOCTOR,TRUE
RADIOLOGY,RAD-XRAY-CHEST,X-Ray Chest PA,7500.00,Chest X-ray,RADIOLOGY,RADIOLOGY_STUDY,TRUE,TRUE,TRUE,BEFORE,DOCTOR,TRUE
PHARMACY,PHARM-PARA,Paracetamol 500mg,500.00,Pain relief,DRUG,DRUG_DISPENSE,TRUE,TRUE,TRUE,AFTER,DOCTOR PHARMACIST,TRUE
PROCEDURE,PROC-SUTURE,Suture Removal,3000.00,Remove sutures,PROCEDURE,PROCEDURE,TRUE,TRUE,TRUE,AFTER,DOCTOR NURSE,TRUE
```

## JSON Format Example

```json
[
  {
    "department": "CONSULTATION",
    "service_code": "GOPD-CONSULT",
    "name": "General Consultation",
    "amount": 5000.00,
    "description": "Standard consultation with a general practitioner",
    "category": "CONSULTATION",
    "workflow_type": "GOPD_CONSULT",
    "requires_visit": true,
    "requires_consultation": false,
    "auto_bill": true,
    "bill_timing": "BEFORE",
    "allowed_roles": ["DOCTOR"],
    "is_active": true
  },
  {
    "department": "LAB",
    "service_code": "LAB-CBC",
    "name": "Complete Blood Count",
    "amount": 2500.00,
    "description": "Full blood count including WBC, RBC, Platelets",
    "category": "LAB",
    "workflow_type": "LAB_ORDER",
    "requires_visit": true,
    "requires_consultation": true,
    "auto_bill": true,
    "bill_timing": "BEFORE",
    "allowed_roles": ["DOCTOR"],
    "is_active": true
  }
]
```

## Department to Category/Workflow Mapping

If `category` or `workflow_type` is not specified, they are automatically inferred from the `department`:

| Department | Default Category | Default Workflow Type |
|------------|------------------|----------------------|
| `CONSULTATION` | `CONSULTATION` | `GOPD_CONSULT` |
| `LAB` | `LAB` | `LAB_ORDER` |
| `PHARMACY` | `DRUG` | `DRUG_DISPENSE` |
| `RADIOLOGY` | `RADIOLOGY` | `RADIOLOGY_STUDY` |
| `PROCEDURE` | `PROCEDURE` | `PROCEDURE` |

## Validation Rules

1. **Service Code**: Must be unique. If a service with the same code exists:
   - Without `--update`: Service is skipped
   - With `--update`: Existing service is updated

2. **Amount**: Must be greater than zero

3. **Department**: Must match one of the valid department choices

4. **Category**: Must be valid for the department:
   - `CONSULTATION` → `CONSULTATION`
   - `LAB` → `LAB`
   - `PHARMACY` → `DRUG`
   - `RADIOLOGY` → `RADIOLOGY`
   - `PROCEDURE` → `PROCEDURE`

5. **Workflow Type**: Must be valid for the department:
   - `CONSULTATION` → `GOPD_CONSULT`, `OTHER`
   - `LAB` → `LAB_ORDER`, `OTHER`
   - `PHARMACY` → `DRUG_DISPENSE`, `OTHER`
   - `RADIOLOGY` → `RADIOLOGY_STUDY`, `OTHER`
   - `PROCEDURE` → `PROCEDURE`, `INJECTION`, `DRESSING`, `VACCINATION`, `PHYSIOTHERAPY`, `OTHER`

6. **Allowed Roles**: Must be valid roles:
   - `ADMIN`, `DOCTOR`, `NURSE`, `LAB_TECH`, `RADIOLOGY_TECH`, `PHARMACIST`, `RECEPTIONIST`, `PATIENT`

7. **Requires Consultation**: If `TRUE`, `requires_visit` must also be `TRUE`

## Tips

1. **Start with a dry run**: Always test your import with `--dry-run` first
   ```bash
   python manage.py import_service_catalog services.csv --dry-run
   ```

2. **Check for errors**: Review the error messages carefully. Common issues:
   - Invalid department names
   - Invalid workflow types for department
   - Duplicate service codes
   - Invalid role names

3. **Update existing services**: Use `--update` to refresh existing services with new data

4. **Excel files**: Make sure column headers are in the first row

5. **CSV files**: The command auto-detects the delimiter (comma, semicolon, tab)

## Example Workflow

```bash
# 1. Test import (dry run)
python manage.py import_service_catalog services.csv --dry-run

# 2. Review output for errors

# 3. Import for real
python manage.py import_service_catalog services.csv

# 4. Update existing services
python manage.py import_service_catalog updated_services.csv --update
```

## Troubleshooting

### "Invalid department"
- Check that department names match exactly: `CONSULTATION`, `LAB`, `PHARMACY`, `RADIOLOGY`, `PROCEDURE`
- Case-sensitive: Use uppercase

### "Invalid workflow_type"
- Ensure workflow type is valid for the department
- Check the mapping table above

### "Validation error"
- The service failed model validation
- Check that all required fields are present
- Verify that `requires_consultation` is not `TRUE` when `requires_visit` is `FALSE`

### "Service code already exists"
- Use `--update` flag to update existing services
- Or change the service code in your import file


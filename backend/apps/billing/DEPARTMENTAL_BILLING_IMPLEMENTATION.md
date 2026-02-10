# Departmental Billing Implementation

## Overview

This document describes the implementation of departmental billing logic with automatic price fetching from service price lists.

## Key Features

✅ **Service Price Lists**: Each department (Lab, Pharmacy, Radiology, Procedures) has its own price list
✅ **Automatic Price Fetching**: Departments CANNOT enter prices manually - prices are fetched automatically
✅ **Validation**: Visit must be OPEN and consultation must exist before adding bill items
✅ **Instant Reflection**: Bill items instantly reflect on receptionist dashboard

## Models

### Price List Models

Each department has its own price list model:

1. **LabServicePriceList** - Laboratory service prices
2. **PharmacyServicePriceList** - Pharmacy/drug prices
3. **RadiologyServicePriceList** - Radiology study prices
4. **ProcedureServicePriceList** - Procedure prices (injections, dressings, etc.)

All price list models inherit from `BasePriceList` and include:
- `service_code`: Unique service identifier
- `service_name`: Service name
- `amount`: Service price
- `description`: Service description
- `is_active`: Whether service is currently available

### ServicePriceListManager

Unified manager class for accessing price lists:

```python
from apps.billing.price_lists import ServicePriceListManager

# Get price for a service
price_info = ServicePriceListManager.get_price('LAB', 'CBC-001')
# Returns: {'service_code': 'CBC-001', 'service_name': 'Complete Blood Count', 'amount': Decimal('5000.00'), 'description': '...'}

# List all services for a department
services = ServicePriceListManager.list_services('LAB', active_only=True)
```

## API Endpoints

### 1. Add Bill Item

**POST** `/api/v1/billing/add-item/`

**Payload:**
```json
{
    "visit_id": 1,
    "department": "LAB",
    "service_code": "CBC-001"
}
```

**Behavior:**
1. Validates visit exists and is OPEN
2. Validates consultation exists for visit
3. Validates department is valid (LAB, PHARMACY, RADIOLOGY, PROCEDURE)
4. Fetches price from price list (automatic - departments cannot enter prices manually)
5. Creates BillItem
6. Attaches to visit bill (creates bill if it doesn't exist)
7. Marks item as UNPAID
8. Auto-recalculates bill totals
9. Returns bill item details with updated bill totals

**Response:**
```json
{
    "id": 1,
    "bill_id": 1,
    "visit_id": 1,
    "department": "LAB",
    "service_code": "CBC-001",
    "service_name": "Complete Blood Count",
    "amount": "5000.00",
    "status": "UNPAID",
    "bill_total_amount": "5000.00",
    "bill_outstanding_balance": "5000.00",
    "created_at": "2024-01-15T10:30:00Z"
}
```

**Error Responses:**
- `400 Bad Request`: Invalid department, missing fields, visit not OPEN, consultation missing
- `404 Not Found`: Visit not found
- `403 Forbidden`: User not authorized (not Receptionist)

### 2. List Services

**GET** `/api/v1/billing/services/?department=LAB&active_only=true`

**Query Parameters:**
- `department`: LAB, PHARMACY, RADIOLOGY, or PROCEDURE (required)
- `active_only`: true/false (default: true)

**Response:**
```json
{
    "department": "LAB",
    "count": 10,
    "services": [
        {
            "service_code": "CBC-001",
            "service_name": "Complete Blood Count",
            "amount": "5000.00",
            "description": "Full CBC test",
            "is_active": true
        },
        ...
    ]
}
```

### 3. Get Service Price

**GET** `/api/v1/billing/service-price/?department=LAB&service_code=CBC-001`

**Query Parameters:**
- `department`: LAB, PHARMACY, RADIOLOGY, or PROCEDURE (required)
- `service_code`: Service code/identifier (required)

**Response:**
```json
{
    "service_code": "CBC-001",
    "service_name": "Complete Blood Count",
    "amount": "5000.00",
    "description": "Full CBC test"
}
```

## Validation Rules

### Visit Validation
- Visit must exist
- Visit status must be OPEN
- Cannot add items to CLOSED visits

### Consultation Validation
- Consultation is NOT required for adding bill items
- Receptionists can add charges from service catalog at any time during an OPEN visit
- Consultation charges are auto-generated when doctor creates consultation

### Department Validation
- Department must be one of: LAB, PHARMACY, RADIOLOGY, PROCEDURE
- Case-insensitive (automatically converted to uppercase)

### Service Code Validation
- Service code must exist in the department's price list
- Service must be active (`is_active=True`)
- Raises `ValidationError` if service not found or inactive

### Permission Validation
- Receptionist and Doctor can add bill items from service catalog
- Enforced via `CanAddServicesFromCatalog` permission class
- Receptionist: Can add services from catalog (billing workflow)
- Doctor: Can order services from catalog (clinical workflow)
- Services ordered by doctors automatically reflect in patient's account in Receptionist dashboard

## Workflow

1. **Receptionist creates visit** for a patient
2. **Receptionist can add bill items** using service codes from price lists (at any time during OPEN visit)
3. **System fetches prices automatically** from price lists
4. **Bill items are created** and attached to visit bill
5. **Bill totals are auto-calculated** (total_amount, amount_paid, outstanding_balance)
6. **Items instantly reflect** on receptionist dashboard
7. **Doctor creates consultation** (when patient is seen)
8. **Consultation charge is auto-generated** by system when consultation is created

## Example Usage

### Adding a Lab Test

```python
# POST /api/v1/billing/add-item/
{
    "visit_id": 1,
    "department": "LAB",
    "service_code": "CBC-001"
}

# System automatically:
# 1. Fetches price from LabServicePriceList
# 2. Creates BillItem with fetched price
# 3. Attaches to visit bill
# 4. Marks as UNPAID
# 5. Recalculates bill totals
```

### Adding a Pharmacy Item

```python
# POST /api/v1/billing/add-item/
{
    "visit_id": 1,
    "department": "PHARMACY",
    "service_code": "PARA-500"
}

# System fetches price from PharmacyServicePriceList
```

### Adding a Radiology Study

```python
# POST /api/v1/billing/add-item/
{
    "visit_id": 1,
    "department": "RADIOLOGY",
    "service_code": "XRAY-CHEST"
}

# System fetches price from RadiologyServicePriceList
```

### Adding a Procedure

```python
# POST /api/v1/billing/add-item/
{
    "visit_id": 1,
    "department": "PROCEDURE",
    "service_code": "INJ-IM"
}

# System fetches price from ProcedureServicePriceList
```

## Price List Management

Price lists are managed through Django Admin:

1. **Lab Services**: Admin → Billing → Lab Service Prices
2. **Pharmacy Services**: Admin → Billing → Pharmacy Service Prices
3. **Radiology Services**: Admin → Billing → Radiology Service Prices
4. **Procedure Services**: Admin → Billing → Procedure Service Prices

**Important**: Departments cannot enter prices manually. All prices must be pre-configured in the price lists.

## Database Tables

- `lab_service_prices` - Lab service price list
- `pharmacy_service_prices` - Pharmacy service price list
- `radiology_service_prices` - Radiology service price list
- `procedure_service_prices` - Procedure service price list
- `bills` - Bill records
- `bill_items` - BillItem records

## Migration

To apply the models to the database:

```bash
python manage.py migrate billing
```

The migration file is: `0009_add_price_lists.py`

## Testing

### Test Cases

1. **Add bill item with valid service code**
   - Should create BillItem
   - Should fetch price from price list
   - Should update bill totals

2. **Add bill item with invalid service code**
   - Should return 400 error
   - Should not create BillItem

3. **Add bill item to CLOSED visit**
   - Should return 400 error
   - Should not create BillItem

4. **Add bill item without consultation**
   - Should return 400 error
   - Should not create BillItem

5. **Add bill item as non-Receptionist**
   - Should return 403 error
   - Should not create BillItem

6. **List services for department**
   - Should return all active services
   - Should respect active_only parameter

7. **Get service price**
   - Should return price for valid service code
   - Should return 400 for invalid service code

## Integration with Receptionist Dashboard

When a bill item is added:
1. Bill totals are automatically recalculated
2. Response includes updated bill totals
3. Frontend can immediately refresh to show new item
4. Outstanding balance is instantly updated

## Security

- Only Receptionist can add bill items (via `CanProcessPayment` permission)
- All actions are logged to AuditLog
- Prices are fetched automatically (no manual entry)
- Visit must be OPEN (prevents modification of closed visits)
- Consultation must exist (ensures proper workflow)


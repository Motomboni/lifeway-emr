# Service Catalog Import Guide

This guide explains how to import clinic services and their prices from an Excel file into the EMR billing system.

## Overview

The EMR system supports importing services from Excel files into the following departmental price lists:
- **LAB**: Laboratory services
- **PHARMACY**: Medications and drugs
- **RADIOLOGY**: Radiology studies and imaging
- **PROCEDURE**: Procedures (injections, dressings, etc.)

## Excel File Format

Your Excel file should have the following columns:

| Column Name | Required | Description | Example |
|------------|----------|-------------|---------|
| Department | Yes | Must be: LAB, PHARMACY, RADIOLOGY, or PROCEDURE | LAB |
| Service Code | Yes | Unique identifier for the service | CBC-001 |
| Service Name | Yes | Name of the service | Complete Blood Count |
| Amount | Yes | Price of the service (numeric) | 5000 |
| Description | No | Optional description | Full CBC test with differential |

### Example Excel Data

```
Department | Service Code | Service Name          | Amount | Description
LAB       | CBC-001      | Complete Blood Count  | 5000   | Full CBC test
LAB       | FBS-001      | Fasting Blood Sugar   | 2000   | FBS test
PHARMACY  | DRUG-001     | Paracetamol 500mg     | 500    | Pain relief medication
PHARMACY  | DRUG-002     | Amoxicillin 500mg     | 1500   | Antibiotic
RADIOLOGY | XRAY-001     | Chest X-Ray           | 3000   | PA and lateral views
PROCEDURE | INJ-001      | Injection Fee         | 500    | Administration fee
```

## Import Methods

There are two ways to import services:

### Method 1: Web-Based Upload (Recommended)

Upload Excel files directly through the API using a web interface.

**Endpoint:** `POST /api/v1/billing/services/import/`

**Request Format:** `multipart/form-data`

**Parameters:**
- `file`: Excel file (.xlsx or .xls) - **Required**
- `update`: true/false (optional, default: false) - Update existing services
- `sheet`: Sheet name or index (optional, default: first sheet)

**Example using cURL:**
```bash
curl -X POST \
  http://localhost:8000/api/v1/billing/services/import/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@services.xlsx" \
  -F "update=false"
```

**Example using JavaScript/TypeScript:**
```typescript
const importServices = async (file: File, updateExisting: boolean = false) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('update', updateExisting.toString());
  
  const response = await fetch('/api/v1/billing/services/import/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${getAuthToken()}`,
    },
    body: formData,
  });
  
  return await response.json();
};

// Usage
const fileInput = document.querySelector('input[type="file"]');
const file = fileInput.files[0];
const result = await importServices(file, false);
console.log(result);
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully imported 95 services. Updated: 5, Skipped: 0",
  "stats": {
    "total": 100,
    "created": 95,
    "updated": 5,
    "skipped": 0,
    "errors": []
  }
}
```

### Method 2: Command Line Import

Import services using Django management command.

**Basic Usage:**
```bash
cd backend
python manage.py import_services /path/to/services.xlsx
```

**Options:**
- `--sheet SHEET_NAME`: Specify sheet name or index (default: first sheet)
- `--dry-run`: Preview changes without saving to database
- `--update`: Update existing services if they already exist (by service code)

**Examples:**

1. **Import from first sheet:**
   ```bash
   python manage.py import_services services.xlsx
   ```

2. **Import from specific sheet:**
   ```bash
   python manage.py import_services services.xlsx --sheet "Services"
   ```

3. **Dry run (preview without saving):**
   ```bash
   python manage.py import_services services.xlsx --dry-run
   ```

4. **Update existing services:**
   ```bash
   python manage.py import_services services.xlsx --update
   ```

## API Endpoints for Frontend

After importing services, the frontend can use these endpoints:

### 1. Service Catalog (Search & Browse)

**GET** `/api/v1/billing/services/catalog/`

Query Parameters:
- `search`: Search term (optional)
- `department`: Filter by department (LAB, PHARMACY, RADIOLOGY, PROCEDURE, or ALL)
- `active_only`: true/false (default: true)
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 50, max: 200)

Example:
```
GET /api/v1/billing/services/catalog/?search=blood&department=LAB&page=1&page_size=20
```

Response:
```json
{
  "count": 45,
  "page": 1,
  "page_size": 20,
  "total_pages": 3,
  "results": [
    {
      "id": 1,
      "department": "LAB",
      "service_code": "CBC-001",
      "service_name": "Complete Blood Count",
      "amount": "5000.00",
      "description": "Full CBC test",
      "is_active": true
    }
  ]
}
```

### 2. Quick Search (Autocomplete)

**GET** `/api/v1/billing/services/search/`

Query Parameters:
- `q`: Search query (required)
- `limit`: Maximum results (default: 20, max: 50)
- `department`: Filter by department (optional)

Example:
```
GET /api/v1/billing/services/search/?q=blood&limit=10
```

Response:
```json
{
  "results": [
    {
      "department": "LAB",
      "service_code": "CBC-001",
      "service_name": "Complete Blood Count",
      "amount": "5000.00",
      "display": "LAB - Complete Blood Count (CBC-001) - ₦5,000.00"
    }
  ]
}
```

## Frontend Integration

### Service Dropdown/Search Component

The Receptionist can use the search endpoint for autocomplete:

```typescript
// Search services as user types
const searchServices = async (query: string) => {
  const response = await apiRequest(
    `/billing/services/search/?q=${encodeURIComponent(query)}&limit=20`
  );
  return response.results;
};

// Get full catalog with pagination
const getServiceCatalog = async (filters: {
  search?: string;
  department?: string;
  page?: number;
}) => {
  const params = new URLSearchParams();
  if (filters.search) params.append('search', filters.search);
  if (filters.department) params.append('department', filters.department);
  if (filters.page) params.append('page', filters.page.toString());
  
  const response = await apiRequest(
    `/billing/services/catalog/?${params.toString()}`
  );
  return response;
};
```

## Validation Rules

The import command validates:

1. **Required columns** must be present
2. **Department** must be one of: LAB, PHARMACY, RADIOLOGY, PROCEDURE
3. **Service Code** must be unique within each department
4. **Service Name** cannot be empty
5. **Amount** must be a positive number

## Error Handling

If errors occur during import:
- Errors are logged and displayed
- Valid rows are still processed
- Invalid rows are skipped
- Summary report shows created/updated/skipped counts

## Next Steps

1. **Prepare your Excel file** with the required columns
2. **Test with dry-run**: `python manage.py import_services services.xlsx --dry-run`
3. **Import services**: `python manage.py import_services services.xlsx`
4. **Verify in Django Admin**: Check that services appear in the admin interface
5. **Test API endpoints**: Verify services are accessible via API
6. **Integrate frontend**: Use the search/catalog endpoints in the billing UI

## Admin Interface

After import, services can be managed in Django Admin:
- **Lab Services**: Admin → Billing → Lab Service Prices
- **Pharmacy Services**: Admin → Billing → Pharmacy Service Prices
- **Radiology Services**: Admin → Billing → Radiology Service Prices
- **Procedure Services**: Admin → Billing → Procedure Service Prices


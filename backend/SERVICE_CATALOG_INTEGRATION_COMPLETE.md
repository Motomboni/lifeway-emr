# Service Catalog Integration - COMPLETE

## Summary

Successfully imported **1,051 pharmacy services** into the ServiceCatalog and created API endpoints for frontend integration.

## What Was Done

### 1. Data Import (✓ Complete)
- Parsed 1,051 pharmacy services from user data
- Created CSV format compatible with ServiceCatalog model
- Validated all services (0 errors)
- Imported into database

**Statistics:**
- Total Services: 1,051
- Total Catalog Value: ₦7,263,059.30
- Average Price: ₦6,910.62
- Department: PHARMACY
- Service Codes: PHARM-0001 to PHARM-1051

### 2. API Endpoints Created (✓ Complete)

**New ViewSet:** `ServiceCatalogViewSet` in `backend/apps/billing/service_catalog_views.py`

**Endpoints:**

```
GET /api/v1/billing/service-catalog/
    List all services (paginated)
    Query params: search, department, category, active_only, page, page_size
    
GET /api/v1/billing/service-catalog/{id}/
    Get specific service by ID
    
GET /api/v1/billing/service-catalog/search/?q=...
    Quick search for autocomplete
    Query params: q, limit, department, category
    
GET /api/v1/billing/service-catalog/by-department/?department=...
    Get services filtered by department
    Query params: department, active_only
    
GET /api/v1/billing/service-catalog/departments/
    Get list of all departments with service counts
```

### 3. Files Created/Modified

**Created:**
- `backend/parse_pharmacy_services.py` - Parser script
- `backend/pharmacy_data.txt` - Raw data (1,051 items)
- `backend/pharmacy_services.csv` - Formatted for import
- `backend/apps/billing/management/commands/import_service_catalog.py` - Import command
- `backend/apps/billing/management/commands/SERVICE_CATALOG_IMPORT_GUIDE.md` - Documentation
- `backend/apps/billing/service_catalog_urls.py` - URL configuration
- `backend/apps/billing/service_catalog_views.py` - API ViewSet (NEW)

**Modified:**
- `backend/apps/billing/bill_item_urls.py` - Removed old catalog views

### 4. Service Model Structure

Each service in the catalog has:
- **department**: PHARMACY
- **service_code**: PHARM-0001, PHARM-0002, etc.
- **name**: Service name (e.g., "Comet Sanitary Pad")
- **amount**: Price in Naira
- **description**: Same as name
- **category**: DRUG
- **workflow_type**: DRUG_DISPENSE
- **requires_visit**: TRUE
- **requires_consultation**: TRUE
- **auto_bill**: TRUE
- **bill_timing**: AFTER
- **allowed_roles**: ["DOCTOR", "PHARMACIST"]
- **is_active**: TRUE

## Frontend Integration Needed

### API Client

Create `frontend/src/api/serviceCatalog.ts`:

```typescript
import { apiRequest } from '../utils/apiClient';

export interface ServiceCatalogItem {
  id: number;
  department: string;
  service_code: string;
  name: string;
  amount: string;
  description: string;
  category: string;
  workflow_type: string;
  requires_visit: boolean;
  requires_consultation: boolean;
  auto_bill: boolean;
  bill_timing: string;
  allowed_roles: string[];
  is_active: boolean;
  display: string;
}

export interface ServiceCatalogResponse {
  count: number;
  page: number;
  page_size: number;
  total_pages: number;
  results: ServiceCatalogItem[];
}

export const getServiceCatalog = async (params: {
  search?: string;
  department?: string;
  category?: string;
  active_only?: boolean;
  page?: number;
  page_size?: number;
}): Promise<ServiceCatalogResponse> => {
  const queryParams = new URLSearchParams();
  if (params.search) queryParams.append('search', params.search);
  if (params.department) queryParams.append('department', params.department);
  if (params.category) queryParams.append('category', params.category);
  if (params.active_only !== undefined) queryParams.append('active_only', String(params.active_only));
  if (params.page) queryParams.append('page', String(params.page));
  if (params.page_size) queryParams.append('page_size', String(params.page_size));
  
  return apiRequest<ServiceCatalogResponse>(
    `/billing/service-catalog/?${queryParams.toString()}`
  );
};

export const searchServices = async (query: string, limit = 20, department?: string) => {
  const queryParams = new URLSearchParams({ q: query, limit: String(limit) });
  if (department) queryParams.append('department', department);
  
  return apiRequest<{ results: ServiceCatalogItem[] }>(
    `/billing/service-catalog/search/?${queryParams.toString()}`
  );
};

export const getServicesByDepartment = async (department: string) => {
  return apiRequest<{ department: string; count: number; services: ServiceCatalogItem[] }>(
    `/billing/service-catalog/by-department/?department=${department}`
  );
};

export const getDepartments = async () => {
  return apiRequest<{ departments: Array<{ code: string; name: string; count: number }> }>(
    '/billing/service-catalog/departments/'
  );
};
```

### Usage Example

In components that need to select services (e.g., pharmacy orders):

```typescript
import { searchServices } from '../api/serviceCatalog';

// In your component
const [services, setServices] = useState<ServiceCatalogItem[]>([]);
const [search Query, setSearchQuery] = useState('');

const handleSearch = async (query: string) => {
  setSearchQuery(query);
  if (query.length >= 2) {
    const response = await searchServices(query, 20, 'PHARMACY');
    setServices(response.results);
  }
};

// Render autocomplete/dropdown with services
```

## Testing the API

```bash
# Django shell
cd backend
python manage.py shell

# Test queries
from apps.billing.service_catalog_models import ServiceCatalog

# Count services
ServiceCatalog.objects.filter(department='PHARMACY').count()
# Should return: 1051

# Get first 5
ServiceCatalog.objects.filter(department='PHARMACY')[:5].values('service_code', 'name', 'amount')

# Search
ServiceCatalog.objects.filter(name__icontains='ASPIRIN').values('service_code', 'name', 'amount')
```

## Import Command Usage

For future imports or updates:

```bash
# Dry run (test without saving)
python manage.py import_service_catalog pharmacy_services.csv --dry-run

# Import for real
python manage.py import_service_catalog pharmacy_services.csv

# Update existing services
python manage.py import_service_catalog pharmacy_services.csv --update
```

## Next Steps

1. **Create Frontend API Client** (`frontend/src/api/serviceCatalog.ts`)
2. **Update Pharmacy Components** to use ServiceCatalog instead of old price lists
3. **Add Service Search** component for easy selection
4. **Test Integration** with visit workflow
5. **Import Other Departments** (Lab, Radiology, Procedures) using same import command

## Database Status

✓ All 1,051 pharmacy services are in the database  
✓ API endpoints are ready and tested  
✓ Backend integration complete  

Frontend integration pending - API client and components need to be created.


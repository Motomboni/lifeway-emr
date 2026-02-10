# Service Catalog Access Guide

This guide explains how Receptionists can access and use clinic services in the billing system.

## Quick Summary

**437 clinic services** are available across 2 departments:
- **PROCEDURE** (391 services): Consultations, Dental, Procedures, ANC, Fertility, Consumables
- **PHARMACY** (46 services): Vaccines, IVF Drugs

**Access Methods:**
1. **Search Box** - Type to search (e.g., "consultation", "dental", "vaccine")
2. **Browse by Department** - Filter by PROCEDURE or PHARMACY
3. **Service Catalog** - Full list with pagination
4. **Django Admin** - Administrative management

**API Endpoints:**
- Quick Search: `/api/v1/billing/services/search/?q=consultation`
- Full Catalog: `/api/v1/billing/services/catalog/?department=PROCEDURE`
- Add to Bill: `POST /api/v1/billing/add-item/`

## Overview

All clinic services (437 services) are stored in departmental price lists and can be accessed through:
1. **API Endpoints** - For frontend integration
2. **Django Admin** - For administrative management
3. **Search & Browse** - Real-time search with autocomplete

## API Endpoints

### 1. Quick Search (Autocomplete/Dropdown)

**Endpoint:** `GET /api/v1/billing/services/search/`

**Purpose:** Fast search for autocomplete suggestions as user types

**Query Parameters:**
- `q` (required): Search query
- `limit` (optional): Max results (default: 20, max: 50)
- `department` (optional): Filter by department (LAB, PHARMACY, RADIOLOGY, PROCEDURE)

**Example Requests:**
```bash
# Search all services
GET /api/v1/billing/services/search/?q=consultation

# Search with department filter
GET /api/v1/billing/services/search/?q=dental&department=PROCEDURE

# Limit results
GET /api/v1/billing/services/search/?q=vaccine&limit=10
```

**Response:**
```json
{
  "results": [
    {
      "department": "PROCEDURE",
      "service_code": "CONS-001-DENTALCONS",
      "service_name": "DENTAL CONSULTATION",
      "amount": "20000.00",
      "display": "PROCEDURE - DENTAL CONSULTATION (CONS-001-DENTALCONS) - ₦20,000.00"
    },
    {
      "department": "PROCEDURE",
      "service_code": "CONS-003-GOPDCONSUL",
      "service_name": "GOPD CONSULTATION",
      "amount": "15000.00",
      "display": "PROCEDURE - GOPD CONSULTATION (CONS-003-GOPDCONSUL) - ₦15,000.00"
    }
  ]
}
```

### 2. Service Catalog (Browse & Filter)

**Endpoint:** `GET /api/v1/billing/services/catalog/`

**Purpose:** Full catalog with pagination, search, and filters

**Query Parameters:**
- `search` (optional): Search term
- `department` (optional): Filter by department (LAB, PHARMACY, RADIOLOGY, PROCEDURE, or ALL)
- `active_only` (optional): true/false (default: true)
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 50, max: 200)

**Example Requests:**
```bash
# Browse all services (first page)
GET /api/v1/billing/services/catalog/

# Search for specific services
GET /api/v1/billing/services/catalog/?search=dental

# Filter by department
GET /api/v1/billing/services/catalog/?department=PHARMACY

# Combined search and filter
GET /api/v1/billing/services/catalog/?search=vaccine&department=PHARMACY&page=1&page_size=20
```

**Response:**
```json
{
  "count": 391,
  "page": 1,
  "page_size": 50,
  "total_pages": 8,
  "results": [
    {
      "id": 1,
      "department": "PROCEDURE",
      "service_code": "CONS-001-DENTALCONS",
      "service_name": "DENTAL CONSULTATION",
      "amount": "20000.00",
      "description": "CLINICAL CONSULTATION service",
      "is_active": true
    },
    {
      "id": 2,
      "department": "PROCEDURE",
      "service_code": "CONS-002-VISITINGPA",
      "service_name": "VISITING PAEDIATRICS CONSULTATION",
      "amount": "45000.00",
      "description": "CLINICAL CONSULTATION service",
      "is_active": true
    }
  ]
}
```

### 3. List Services by Department

**Endpoint:** `GET /api/v1/billing/services/?department=PROCEDURE`

**Purpose:** List all services for a specific department

**Query Parameters:**
- `department` (required): LAB, PHARMACY, RADIOLOGY, or PROCEDURE
- `active_only` (optional): true/false (default: true)

**Example:**
```bash
GET /api/v1/billing/services/?department=PROCEDURE&active_only=true
```

### 4. Get Service Price

**Endpoint:** `GET /api/v1/billing/service-price/?department=PROCEDURE&service_code=CONS-001-DENTALCONS`

**Purpose:** Get price for a specific service

**Query Parameters:**
- `department` (required): Department name
- `service_code` (required): Service code

**Response:**
```json
{
  "service_code": "CONS-001-DENTALCONS",
  "service_name": "DENTAL CONSULTATION",
  "amount": "20000.00",
  "description": "CLINICAL CONSULTATION service"
}
```

### 5. Add Service to Bill

**Endpoint:** `POST /api/v1/billing/add-item/`

**Purpose:** Add a service to a visit's bill

**Request Body:**
```json
{
  "visit_id": 123,
  "department": "PROCEDURE",
  "service_code": "CONS-001-DENTALCONS"
}
```

**Response:**
```json
{
  "id": 456,
  "bill_id": 789,
  "visit_id": 123,
  "department": "PROCEDURE",
  "service_code": "CONS-001-DENTALCONS",
  "service_name": "DENTAL CONSULTATION",
  "amount": "20000.00",
  "status": "UNPAID",
  "bill_total_amount": "20000.00",
  "bill_outstanding_balance": "20000.00",
  "created_at": "2024-01-15T10:30:00Z"
}
```

## Frontend Integration Examples

### React/TypeScript Example

```typescript
// Service search hook
import { useState, useEffect } from 'react';
import { apiRequest } from '../utils/apiClient';

interface Service {
  department: string;
  service_code: string;
  service_name: string;
  amount: string;
  display: string;
}

export function useServiceSearch(query: string, department?: string) {
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!query || query.length < 2) {
      setServices([]);
      return;
    }

    setLoading(true);
    const params = new URLSearchParams({ q: query });
    if (department) params.append('department', department);

    apiRequest<{ results: Service[] }>(`/billing/services/search/?${params}`)
      .then((data) => setServices(data.results))
      .catch((error) => console.error('Search error:', error))
      .finally(() => setLoading(false));
  }, [query, department]);

  return { services, loading };
}

// Service catalog hook
export function useServiceCatalog(filters: {
  search?: string;
  department?: string;
  page?: number;
}) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (filters.search) params.append('search', filters.search);
    if (filters.department) params.append('department', filters.department);
    if (filters.page) params.append('page', filters.page.toString());

    apiRequest(`/billing/services/catalog/?${params}`)
      .then(setData)
      .catch((error) => console.error('Catalog error:', error))
      .finally(() => setLoading(false));
  }, [filters.search, filters.department, filters.page]);

  return { data, loading };
}

// Add service to bill
export async function addServiceToBill(
  visitId: number,
  department: string,
  serviceCode: string
) {
  return apiRequest('/billing/add-item/', {
    method: 'POST',
    body: JSON.stringify({
      visit_id: visitId,
      department,
      service_code: serviceCode,
    }),
  });
}
```

### Service Search Component Example

```typescript
import React, { useState } from 'react';
import { useServiceSearch } from '../hooks/useServiceSearch';

export function ServiceSearchDropdown({
  onSelect,
  department,
}: {
  onSelect: (service: Service) => void;
  department?: string;
}) {
  const [query, setQuery] = useState('');
  const { services, loading } = useServiceSearch(query, department);

  return (
    <div className="service-search">
      <input
        type="text"
        placeholder="Search services..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="service-search-input"
      />
      
      {loading && <div>Searching...</div>}
      
      {services.length > 0 && (
        <ul className="service-dropdown">
          {services.map((service) => (
            <li
              key={service.service_code}
              onClick={() => {
                onSelect(service);
                setQuery('');
              }}
            >
              <div className="service-name">{service.service_name}</div>
              <div className="service-code">{service.service_code}</div>
              <div className="service-amount">₦{parseFloat(service.amount).toLocaleString()}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

## User Workflow

### For Receptionists:

1. **Open Visit Details Page**
   - Navigate to the visit for which billing is needed
   - Click on "Billing" section

2. **Search for Service**
   - Type in the search box (e.g., "consultation", "dental", "vaccine")
   - See autocomplete suggestions with prices
   - Or browse by department using filters

3. **Select Service**
   - Click on a service from the dropdown
   - Service is automatically added to the bill with its price
   - Price is fetched automatically from the price list

4. **Add Multiple Services**
   - Repeat search and select for additional services
   - All services are added to the same bill

5. **Process Payment**
   - After adding all services, process payment
   - Bill total is calculated automatically

## Service Categories

Services are organized by department:

- **PROCEDURE** (391 services):
  - Clinical Consultations
  - Dental Services
  - Surgical Procedures
  - ANC Services
  - Fertility Services
  - Consumables

- **PHARMACY** (46 services):
  - Vaccines
  - IVF Drugs
  - Medications

## Search Tips

1. **Search by name**: Type part of the service name (e.g., "dental", "consultation")
2. **Search by code**: Type the service code (e.g., "CONS-001")
3. **Filter by department**: Use department filter to narrow results
4. **Case insensitive**: Search is case-insensitive

## Example Searches

```bash
# Find all consultations
GET /api/v1/billing/services/search/?q=consultation

# Find dental services
GET /api/v1/billing/services/search/?q=dental&department=PROCEDURE

# Find vaccines
GET /api/v1/billing/services/search/?q=vaccine&department=PHARMACY

# Find IVF services
GET /api/v1/billing/services/search/?q=IVF

# Find procedures under 50,000
GET /api/v1/billing/services/catalog/?department=PROCEDURE&page_size=200
# Then filter client-side by amount < 50000
```

## Authentication

All endpoints require:
- **Authentication**: Valid JWT token in `Authorization: Bearer <token>` header
- **Permissions**: 
  - Search/Catalog: Any authenticated user
  - Add to Bill: Receptionist role only (`CanProcessPayment` permission)

## Error Handling

If a service is not found:
```json
{
  "detail": "Service with code 'INVALID-CODE' not found in PROCEDURE price list or service is inactive."
}
```

If visit is not OPEN:
```json
{
  "detail": "Cannot add bill items to a CLOSED visit. Visit must be OPEN."
}
```

## Next Steps

1. **Frontend Integration**: Implement the search component in your billing UI
2. **Testing**: Test the search functionality with various queries
3. **User Training**: Train Receptionists on how to search and select services
4. **Monitoring**: Monitor service usage and add more services as needed


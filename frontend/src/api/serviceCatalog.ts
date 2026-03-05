/**
 * Service Catalog API Client
 *
 * - GET    /api/v1/billing/service-catalog/           - List services (paginated)
 * - POST   /api/v1/billing/service-catalog/           - Create service (admin)
 * - GET    /api/v1/billing/service-catalog/{id}/     - Get service
 * - PUT    /api/v1/billing/service-catalog/{id}/     - Update service (admin)
 * - PATCH  /api/v1/billing/service-catalog/{id}/      - Partial update (admin)
 * - DELETE /api/v1/billing/service-catalog/{id}/     - Delete service (admin)
 * - GET    /api/v1/billing/service-catalog/choices/   - Get choices for forms
 * - POST   /api/v1/billing/service-catalog/import/    - Import from Excel
 */
import { apiRequest, getAuthToken } from '../utils/apiClient';
import type {
  ServiceCatalogItem,
  ServiceCatalogCreate,
  ServiceCatalogUpdate,
  ServiceCatalogListResponse,
  ServiceCatalogChoices,
} from '../types/serviceCatalog';

export async function fetchServiceCatalog(params?: {
  page?: number;
  page_size?: number;
  department?: string;
  active_only?: boolean;
  search?: string;
}): Promise<ServiceCatalogListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page != null) searchParams.set('page', String(params.page));
  if (params?.page_size != null) searchParams.set('page_size', String(params.page_size));
  if (params?.department) searchParams.set('department', params.department);
  if (params?.active_only !== undefined) searchParams.set('active_only', String(params.active_only));
  if (params?.search) searchParams.set('search', params.search);
  const query = searchParams.toString();
  const url = query ? `/billing/service-catalog/?${query}` : '/billing/service-catalog/';
  return apiRequest<ServiceCatalogListResponse>(url);
}

export async function getServiceCatalogItem(id: number): Promise<ServiceCatalogItem> {
  return apiRequest<ServiceCatalogItem>(`/billing/service-catalog/${id}/`);
}

export async function createServiceCatalog(
  data: ServiceCatalogCreate
): Promise<ServiceCatalogItem> {
  return apiRequest<ServiceCatalogItem>('/billing/service-catalog/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateServiceCatalog(
  id: number,
  data: ServiceCatalogUpdate
): Promise<ServiceCatalogItem> {
  return apiRequest<ServiceCatalogItem>(`/billing/service-catalog/${id}/`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function patchServiceCatalog(
  id: number,
  data: ServiceCatalogUpdate
): Promise<ServiceCatalogItem> {
  return apiRequest<ServiceCatalogItem>(`/billing/service-catalog/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function deleteServiceCatalog(id: number): Promise<void> {
  return apiRequest<void>(`/billing/service-catalog/${id}/`, {
    method: 'DELETE',
  });
}

export async function fetchServiceCatalogChoices(): Promise<ServiceCatalogChoices> {
  return apiRequest<ServiceCatalogChoices>('/billing/service-catalog/choices/');
}

export interface ServiceCatalogImportStats {
  total: number;
  created: number;
  updated: number;
  skipped: number;
  errors: string[];
}

export interface ServiceCatalogImportResponse {
  success: boolean;
  message: string;
  stats: ServiceCatalogImportStats;
}

const API_BASE = process.env.REACT_APP_API_URL || '/api/v1';

export async function importServiceCatalogFromExcel(
  file: File,
  options?: { update?: boolean; sheet?: string | number }
): Promise<ServiceCatalogImportResponse> {
  const formData = new FormData();
  formData.append('file', file);
  if (options?.update) formData.append('update', 'true');
  if (options?.sheet != null) formData.append('sheet', String(options.sheet));

  const token = getAuthToken();
  if (!token) throw new Error('Not authenticated');

  const response = await fetch(`${API_BASE}/billing/service-catalog/import/`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(
      (Array.isArray(data.detail) ? data.detail.join(' ') : data.detail) ||
        data.message ||
        'Import failed'
    );
  }
  return data;
}

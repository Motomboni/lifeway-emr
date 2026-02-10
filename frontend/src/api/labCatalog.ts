/**
 * API client for Lab Test Catalog.
 */
import { apiRequest } from '../utils/apiClient';
import {
  LabTestCatalog,
  LabTestCatalogCreate,
  LabTestCatalogUpdate,
  LabTestCategory,
} from '../types/labCatalog';

export interface LabTestCatalogFilters {
  category?: LabTestCategory;
  is_active?: boolean;
  search?: string;
}

/**
 * Fetch lab test catalog entries
 */
export async function fetchLabTestCatalog(
  filters?: LabTestCatalogFilters
): Promise<LabTestCatalog[]> {
  const queryParams = new URLSearchParams();
  if (filters?.category) {
    queryParams.append('category', filters.category);
  }
  if (filters?.is_active !== undefined) {
    queryParams.append('is_active', filters.is_active.toString());
  }
  if (filters?.search) {
    queryParams.append('search', filters.search);
  }
  
  const queryString = queryParams.toString();
  const url = `/laboratory/lab-tests/${queryString ? `?${queryString}` : ''}`;
  
  const data = await apiRequest<LabTestCatalog[]>(url);
  return Array.isArray(data) ? data : [];
}

/**
 * Fetch active lab tests only
 */
export async function fetchActiveLabTests(): Promise<LabTestCatalog[]> {
  const data = await apiRequest<LabTestCatalog[]>('/laboratory/lab-tests/active/');
  return Array.isArray(data) ? data : [];
}

/**
 * Fetch a single lab test catalog entry
 */
export async function getLabTestCatalog(testId: number): Promise<LabTestCatalog> {
  return apiRequest<LabTestCatalog>(`/laboratory/lab-tests/${testId}/`);
}

/**
 * Create a lab test catalog entry
 */
export async function createLabTestCatalog(
  data: LabTestCatalogCreate
): Promise<LabTestCatalog> {
  return apiRequest<LabTestCatalog>('/laboratory/lab-tests/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Update a lab test catalog entry
 */
export async function updateLabTestCatalog(
  testId: number,
  data: LabTestCatalogUpdate
): Promise<LabTestCatalog> {
  return apiRequest<LabTestCatalog>(`/laboratory/lab-tests/${testId}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Delete a lab test catalog entry
 */
export async function deleteLabTestCatalog(testId: number): Promise<void> {
  await apiRequest(`/laboratory/lab-tests/${testId}/`, {
    method: 'DELETE',
  });
}

/**
 * Get available categories
 */
export async function getLabTestCategories(): Promise<string[]> {
  const response = await apiRequest<{ categories: string[] }>('/laboratory/lab-tests/categories/');
  return response.categories || [];
}

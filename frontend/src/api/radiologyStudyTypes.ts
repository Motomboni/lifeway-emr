/**
 * API client for Radiology Study Types Catalog.
 */
import { apiRequest } from '../utils/apiClient';
import {
  RadiologyStudyType,
  RadiologyStudyTypeCreate,
  RadiologyStudyTypeUpdate,
  RadiologyStudyCategory,
} from '../types/radiologyStudyTypes';

export interface RadiologyStudyTypeFilters {
  category?: RadiologyStudyCategory;
  is_active?: boolean;
  contrast_required?: boolean;
  search?: string;
}

/**
 * Fetch radiology study types catalog entries
 */
export async function fetchRadiologyStudyTypes(
  filters?: RadiologyStudyTypeFilters
): Promise<RadiologyStudyType[]> {
  const queryParams = new URLSearchParams();
  if (filters?.category) {
    queryParams.append('category', filters.category);
  }
  if (filters?.is_active !== undefined) {
    queryParams.append('is_active', filters.is_active.toString());
  }
  if (filters?.contrast_required !== undefined) {
    queryParams.append('contrast_required', filters.contrast_required.toString());
  }
  if (filters?.search) {
    queryParams.append('search', filters.search);
  }
  
  const queryString = queryParams.toString();
  const url = `/radiology/study-types/${queryString ? `?${queryString}` : ''}`;
  
  const data = await apiRequest<RadiologyStudyType[]>(url);
  return Array.isArray(data) ? data : [];
}

/**
 * Fetch active radiology study types only
 */
export async function fetchActiveRadiologyStudyTypes(): Promise<RadiologyStudyType[]> {
  const data = await apiRequest<RadiologyStudyType[]>('/radiology/study-types/active/');
  return Array.isArray(data) ? data : [];
}

/**
 * Fetch a single radiology study type catalog entry
 */
export async function getRadiologyStudyType(studyTypeId: number): Promise<RadiologyStudyType> {
  return apiRequest<RadiologyStudyType>(`/radiology/study-types/${studyTypeId}/`);
}

/**
 * Create a radiology study type catalog entry
 */
export async function createRadiologyStudyType(
  data: RadiologyStudyTypeCreate
): Promise<RadiologyStudyType> {
  return apiRequest<RadiologyStudyType>('/radiology/study-types/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Update a radiology study type catalog entry
 */
export async function updateRadiologyStudyType(
  studyTypeId: number,
  data: RadiologyStudyTypeUpdate
): Promise<RadiologyStudyType> {
  return apiRequest<RadiologyStudyType>(`/radiology/study-types/${studyTypeId}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Delete a radiology study type catalog entry
 */
export async function deleteRadiologyStudyType(studyTypeId: number): Promise<void> {
  await apiRequest(`/radiology/study-types/${studyTypeId}/`, {
    method: 'DELETE',
  });
}

/**
 * Get available categories
 */
export async function getRadiologyStudyCategories(): Promise<string[]> {
  const response = await apiRequest<{ categories: string[] }>('/radiology/study-types/categories/');
  return response.categories || [];
}

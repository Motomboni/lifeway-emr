/**
 * Drug API Client
 * 
 * Endpoints:
 * - GET    /api/v1/drugs/          - List all drugs
 * - POST   /api/v1/drugs/          - Create drug (Pharmacist only)
 * - GET    /api/v1/drugs/{id}/     - Get drug details
 * - PUT    /api/v1/drugs/{id}/     - Update drug (Pharmacist only)
 * - PATCH  /api/v1/drugs/{id}/     - Partial update drug (Pharmacist only)
 * - DELETE /api/v1/drugs/{id}/     - Delete drug (Pharmacist only, soft delete)
 */
import { Drug, DrugCreateData, DrugUpdateData } from '../types/drug';
import { apiRequest } from '../utils/apiClient';

// Re-export types for convenience
export type { Drug, DrugCreateData, DrugUpdateData } from '../types/drug';

/**
 * Paginated response type for drugs
 */
export interface PaginatedDrugResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Drug[];
}

/**
 * Fetch all drugs
 * Returns either an array or paginated response depending on backend configuration
 */
export async function fetchDrugs(): Promise<Drug[] | PaginatedDrugResponse> {
  return apiRequest<Drug[] | PaginatedDrugResponse>('/drugs/');
}

/**
 * Fetch a single drug by ID
 */
export async function fetchDrug(drugId: number): Promise<Drug> {
  return apiRequest<Drug>(`/drugs/${drugId}/`);
}

/**
 * Create a new drug (Pharmacist only)
 */
export async function createDrug(drugData: DrugCreateData): Promise<Drug> {
  return apiRequest<Drug>('/drugs/', {
    method: 'POST',
    body: JSON.stringify(drugData),
  });
}

/**
 * Update a drug (Pharmacist only)
 */
export async function updateDrug(
  drugId: number,
  drugData: DrugUpdateData
): Promise<Drug> {
  return apiRequest<Drug>(`/drugs/${drugId}/`, {
    method: 'PUT',
    body: JSON.stringify(drugData),
  });
}

/**
 * Partial update a drug (Pharmacist only)
 */
export async function partialUpdateDrug(
  drugId: number,
  drugData: Partial<DrugUpdateData>
): Promise<Drug> {
  return apiRequest<Drug>(`/drugs/${drugId}/`, {
    method: 'PATCH',
    body: JSON.stringify(drugData),
  });
}

/**
 * Delete a drug (Pharmacist only, soft delete)
 */
export async function deleteDrug(drugId: number): Promise<void> {
  return apiRequest<void>(`/drugs/${drugId}/`, {
    method: 'DELETE',
  });
}

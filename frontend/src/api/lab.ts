/**
 * Lab Order and Result API Client
 * 
 * All endpoints are visit-scoped:
 * - GET    /api/v1/visits/{visitId}/laboratory/          - List lab orders
 * - POST   /api/v1/visits/{visitId}/laboratory/          - Create lab order (Doctor)
 * - GET    /api/v1/visits/{visitId}/laboratory/results/   - List lab results
 * - POST   /api/v1/visits/{visitId}/laboratory/results/   - Create lab result (Lab Tech)
 */
import { LabOrder, LabOrderCreateData, LabResult, LabResultCreateData } from '../types/lab';
import { apiRequest } from '../utils/apiClient';

// Re-export types for convenience
export type { LabOrder, LabOrderCreateData, LabResult, LabResultCreateData } from '../types/lab';

/**
 * Fetch lab orders for a visit
 */
export async function fetchLabOrders(visitId: string): Promise<LabOrder[]> {
  return apiRequest<LabOrder[]>(`/visits/${visitId}/laboratory/`);
}

/**
 * Create a new lab order (Doctor only)
 */
export async function createLabOrder(
  visitId: string,
  labOrderData: LabOrderCreateData
): Promise<LabOrder> {
  return apiRequest<LabOrder>(`/visits/${visitId}/laboratory/`, {
    method: 'POST',
    body: JSON.stringify(labOrderData),
  });
}

/**
 * Fetch lab results for a visit
 */
export async function fetchLabResults(visitId: string): Promise<LabResult[]> {
  return apiRequest<LabResult[]>(`/visits/${visitId}/laboratory/results/`);
}

/**
 * Create a new lab result (Lab Tech only)
 */
export async function createLabResult(
  visitId: string,
  labResultData: LabResultCreateData
): Promise<LabResult> {
  return apiRequest<LabResult>(`/visits/${visitId}/laboratory/results/`, {
    method: 'POST',
    body: JSON.stringify(labResultData),
  });
}

/**
 * Lab Test Template Types
 */
export interface LabTestTemplate {
  id: number;
  name: string;
  category: string;
  description: string;
  tests: string[];
  default_clinical_indication: string;
  created_by: number;
  created_by_name?: string;
  is_active: boolean;
  usage_count: number;
  created_at: string;
  updated_at: string;
}

export interface LabTestTemplateUseResponse {
  tests: string[];
  clinical_indication: string;
}

/**
 * Fetch lab test templates
 */
export async function fetchLabTestTemplates(category?: string): Promise<LabTestTemplate[]> {
  const params = new URLSearchParams();
  if (category) {
    params.append('category', category);
  }
  const queryString = params.toString();
  const url = `/lab-templates/templates/${queryString ? `?${queryString}` : ''}`;
  const response = await apiRequest<any>(url);
  // Handle paginated response (DRF may return {results: [...], count: ...})
  if (response && typeof response === 'object' && 'results' in response) {
    return response.results as LabTestTemplate[];
  }
  // Handle direct array response
  return Array.isArray(response) ? response : [];
}

/**
 * Apply a lab test template (increments usage count and returns template data)
 */
export async function applyLabTestTemplate(templateId: number): Promise<LabTestTemplateUseResponse> {
  return apiRequest<LabTestTemplateUseResponse>(
    `/lab-templates/templates/${templateId}/use/`,
    {
      method: 'POST',
    }
  );
}
/**
 * Diagnosis Codes API Client
 * 
 * All endpoints are visit-scoped:
 * - GET    /api/v1/visits/{visitId}/consultation/diagnosis-codes/
 * - POST   /api/v1/visits/{visitId}/consultation/diagnosis-codes/
 * - GET    /api/v1/visits/{visitId}/consultation/diagnosis-codes/{id}/
 * - PUT    /api/v1/visits/{visitId}/consultation/diagnosis-codes/{id}/
 * - PATCH  /api/v1/visits/{visitId}/consultation/diagnosis-codes/{id}/
 * - DELETE /api/v1/visits/{visitId}/consultation/diagnosis-codes/{id}/
 * - POST   /api/v1/visits/{visitId}/consultation/diagnosis-codes/from-ai-suggestion/
 */
import { apiRequest } from '../utils/apiClient';
import type { DiagnosisCode, DiagnosisCodeData, ApplyAICodesRequest } from '../types/consultation';

/**
 * Get all diagnosis codes for a consultation
 */
export async function getDiagnosisCodes(visitId: string): Promise<DiagnosisCode[]> {
  return apiRequest<DiagnosisCode[]>(`/visits/${visitId}/consultation/diagnosis-codes/`);
}

/**
 * Create a diagnosis code
 */
export async function createDiagnosisCode(
  visitId: string,
  data: DiagnosisCodeData
): Promise<DiagnosisCode> {
  return apiRequest<DiagnosisCode>(`/visits/${visitId}/consultation/diagnosis-codes/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Update a diagnosis code
 */
export async function updateDiagnosisCode(
  visitId: string,
  codeId: number,
  data: Partial<DiagnosisCodeData>
): Promise<DiagnosisCode> {
  return apiRequest<DiagnosisCode>(`/visits/${visitId}/consultation/diagnosis-codes/${codeId}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Delete a diagnosis code
 */
export async function deleteDiagnosisCode(visitId: string, codeId: number): Promise<void> {
  return apiRequest<void>(`/visits/${visitId}/consultation/diagnosis-codes/${codeId}/`, {
    method: 'DELETE',
  });
}

/**
 * Apply AI-suggested diagnosis codes
 */
export async function applyAIDiagnosisCodes(
  visitId: string,
  request: ApplyAICodesRequest
): Promise<DiagnosisCode[]> {
  return apiRequest<DiagnosisCode[]>(
    `/visits/${visitId}/consultation/diagnosis-codes/from-ai-suggestion/`,
    {
      method: 'POST',
      body: JSON.stringify(request),
    }
  );
}


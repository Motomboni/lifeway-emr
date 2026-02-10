/**
 * Consultation API Client
 * 
 * API Interaction Outline:
 * 
 * All endpoints are visit-scoped:
 * - GET    /api/v1/visits/{visitId}/consultation/     - Fetch consultation
 * - POST   /api/v1/visits/{visitId}/consultation/     - Create consultation
 * - PATCH  /api/v1/visits/{visitId}/consultation/     - Update consultation
 * 
 * Authentication:
 * - JWT token in Authorization header
 * - Token obtained from auth context/store
 * 
 * Error Handling:
 * - 401: Unauthorized - redirect to login
 * - 403: Forbidden - show error (payment/role/status issue)
 * - 404: Not found - consultation doesn't exist (expected for new)
 * - 409: Conflict - visit is CLOSED
 * - 500: Server error - show error message
 */
import { ConsultationData, Consultation } from '../types/consultation';

import { apiRequest } from '../utils/apiClient';

/**
 * Fetch consultation for a visit
 */
export async function fetchConsultation(visitId: string): Promise<Consultation> {
  const data = await apiRequest<Consultation[]>(
    `/visits/${visitId}/consultation/`
  );
  
  // API returns array, but OneToOneField means only one consultation
  if (Array.isArray(data) && data.length > 0) {
    return data[0];
  }
  
  throw new Error('404');
}

/**
 * Create a new consultation
 */
export async function createConsultation(
  visitId: string,
  consultationData: ConsultationData
): Promise<Consultation> {
  return apiRequest<Consultation>(`/visits/${visitId}/consultation/`, {
    method: 'POST',
    body: JSON.stringify(consultationData),
  });
}

/**
 * Update an existing consultation
 */
export async function updateConsultation(
  visitId: string,
  consultationData: Partial<ConsultationData>
): Promise<Consultation> {
  return apiRequest<Consultation>(`/visits/${visitId}/consultation/`, {
    method: 'PATCH',
    body: JSON.stringify(consultationData),
  });
}

/**
 * Fetch all previous consultations for the patient in this visit
 * 
 * Returns an empty array if no previous consultations are found.
 */
export async function fetchPatientConsultations(visitId: string): Promise<Consultation[]> {
  try {
    const response = await apiRequest<{ count: number; results: Consultation[] }>(
      `/visits/${visitId}/consultation/patient-consultations/`
    );
    return response.results || [];
  } catch (error: any) {
    // If 404 or empty response, return empty array (no previous consultations)
    if (error.status === 404 || error.status === 200) {
      return [];
    }
    throw error;
  }
}

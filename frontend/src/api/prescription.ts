/**
 * Prescription API Client
 * 
 * All endpoints are visit-scoped:
 * - GET    /api/v1/visits/{visitId}/prescriptions/          - List prescriptions
 * - POST   /api/v1/visits/{visitId}/prescriptions/          - Create prescription (Doctor)
 * - GET    /api/v1/visits/{visitId}/prescriptions/{id}/     - Get prescription
 * - POST   /api/v1/visits/{visitId}/pharmacy/dispense/      - Dispense prescription (Pharmacist)
 */
import { Prescription, PrescriptionCreateData } from '../types/prescription';
import { Visit } from '../types/visit';
import { apiRequest } from '../utils/apiClient';

// Re-export types for convenience
export type { Prescription, PrescriptionCreateData } from '../types/prescription';

interface WorklistResponse<T> {
  count: number;
  page: number;
  page_size: number;
  results: T[];
}

/**
 * Fetch prescriptions for a visit
 */
export async function fetchPrescriptions(visitId: string): Promise<Prescription[]> {
  return apiRequest<Prescription[]>(`/visits/${visitId}/prescriptions/`);
}

export async function fetchPrescriptionWorklist(status: 'all' | 'pending' = 'all'): Promise<Visit[]> {
  const response = await apiRequest<WorklistResponse<Visit>>(
    `/drugs/prescriptions/worklist/?status=${status}&page_size=500`
  );
  return response.results || [];
}

/**
 * Create a new prescription (Doctor only)
 */
export async function createPrescription(
  visitId: string,
  prescriptionData: PrescriptionCreateData
): Promise<Prescription> {
  return apiRequest<Prescription>(`/visits/${visitId}/prescriptions/`, {
    method: 'POST',
    body: JSON.stringify(prescriptionData),
  });
}

/**
 * Dispense a prescription (Pharmacist only)
 */
export async function dispensePrescription(
  visitId: string,
  prescriptionId: number,
  dispensedQuantity?: string,
  dispensingNotes?: string
): Promise<Prescription> {
  return apiRequest<Prescription>(`/visits/${visitId}/pharmacy/dispense/`, {
    method: 'POST',
    body: JSON.stringify({
      prescription_id: prescriptionId,
      dispensed_quantity: dispensedQuantity || '',
      dispensing_notes: dispensingNotes || ''
    }),
  });
}

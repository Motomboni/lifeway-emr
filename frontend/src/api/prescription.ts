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
import { apiRequest } from '../utils/apiClient';

// Re-export types for convenience
export type { Prescription, PrescriptionCreateData } from '../types/prescription';

/**
 * Fetch prescriptions for a visit
 */
export async function fetchPrescriptions(visitId: string): Promise<Prescription[]> {
  return apiRequest<Prescription[]>(`/visits/${visitId}/prescriptions/`);
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
  dispensingNotes?: string
): Promise<Prescription> {
  return apiRequest<Prescription>(`/visits/${visitId}/pharmacy/dispense/`, {
    method: 'POST',
    body: JSON.stringify({
      prescription_id: prescriptionId,
      dispensing_notes: dispensingNotes || ''
    }),
  });
}

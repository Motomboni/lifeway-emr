/**
 * Structured patient allergies API — /api/v1/patients/{patientId}/allergies/
 */
import { apiRequest } from '../utils/apiClient';

export type AllergenType = 'DRUG' | 'FOOD' | 'ENVIRONMENT' | 'OTHER' | 'UNKNOWN';
export type AllergySeverity = 'MILD' | 'MODERATE' | 'SEVERE' | 'UNKNOWN';

export interface PatientAllergy {
  id: number;
  patient: number;
  allergen: string;
  allergen_type: AllergenType;
  severity: AllergySeverity;
  reaction: string;
  onset_date?: string | null;
  verified: boolean;
  source: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PatientAllergyCreate {
  allergen: string;
  allergen_type?: AllergenType;
  severity?: AllergySeverity;
  reaction?: string;
  verified?: boolean;
}

export interface StructuredAllergySummary {
  id: number;
  allergen: string;
  allergen_type: string;
  severity: string;
  reaction: string;
  verified: boolean;
}

export async function fetchPatientAllergies(patientId: number): Promise<PatientAllergy[]> {
  return apiRequest<PatientAllergy[]>(`/patients/${patientId}/allergies/`);
}

export async function createPatientAllergy(
  patientId: number,
  data: PatientAllergyCreate,
): Promise<PatientAllergy> {
  return apiRequest<PatientAllergy>(`/patients/${patientId}/allergies/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function deactivatePatientAllergy(
  patientId: number,
  allergyId: number,
): Promise<void> {
  await apiRequest(`/patients/${patientId}/allergies/${allergyId}/`, {
    method: 'DELETE',
  });
}

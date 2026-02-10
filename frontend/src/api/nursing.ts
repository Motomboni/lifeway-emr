/**
 * Nursing API Client
 * 
 * All endpoints are visit-scoped:
 * - POST /api/v1/visits/{visit_id}/vitals/ - Create vital signs
 * - GET /api/v1/visits/{visit_id}/vitals/ - List vital signs
 * - POST /api/v1/visits/{visit_id}/nursing-notes/ - Create nursing note
 * - GET /api/v1/visits/{visit_id}/nursing-notes/ - List nursing notes
 * - POST /api/v1/visits/{visit_id}/medication-administration/ - Create medication administration
 * - GET /api/v1/visits/{visit_id}/medication-administration/ - List medication administrations
 * - POST /api/v1/visits/{visit_id}/lab-samples/ - Create lab sample collection
 * - GET /api/v1/visits/{visit_id}/lab-samples/ - List lab sample collections
 */
import { apiRequest } from '../utils/apiClient';
import {
  NursingNote,
  NursingNoteCreate,
  MedicationAdministration,
  MedicationAdministrationCreate,
  LabSampleCollection,
  LabSampleCollectionCreate,
} from '../types/nursing';
import { VitalSigns, VitalSignsCreate } from '../types/clinical';

/**
 * Create vital signs (Nurse endpoint)
 */
export async function createVitalSignsNurse(
  visitId: number,
  data: VitalSignsCreate
): Promise<VitalSigns> {
  return apiRequest<VitalSigns>(`/visits/${visitId}/vitals/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Fetch vital signs (Nurse endpoint)
 */
export async function fetchVitalSignsNurse(visitId: number): Promise<VitalSigns[]> {
  return apiRequest<VitalSigns[]>(`/visits/${visitId}/vitals/`);
}

/**
 * Create nursing note
 */
export async function createNursingNote(
  visitId: number,
  data: NursingNoteCreate
): Promise<NursingNote> {
  return apiRequest<NursingNote>(`/visits/${visitId}/nursing-notes/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Fetch nursing notes for a visit
 */
export async function fetchNursingNotes(visitId: number): Promise<NursingNote[]> {
  return apiRequest<NursingNote[]>(`/visits/${visitId}/nursing-notes/`);
}

/**
 * Update nursing note
 */
export async function updateNursingNote(
  visitId: number,
  noteId: number,
  data: NursingNoteCreate
): Promise<NursingNote> {
  return apiRequest<NursingNote>(`/visits/${visitId}/nursing-notes/${noteId}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Create medication administration
 */
export async function createMedicationAdministration(
  visitId: number,
  data: MedicationAdministrationCreate
): Promise<MedicationAdministration> {
  return apiRequest<MedicationAdministration>(`/visits/${visitId}/medication-administration/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Fetch medication administrations for a visit
 */
export async function fetchMedicationAdministrations(
  visitId: number
): Promise<MedicationAdministration[]> {
  return apiRequest<MedicationAdministration[]>(`/visits/${visitId}/medication-administration/`);
}

/**
 * Update medication administration
 */
export async function updateMedicationAdministration(
  visitId: number,
  administrationId: number,
  data: MedicationAdministrationCreate
): Promise<MedicationAdministration> {
  return apiRequest<MedicationAdministration>(`/visits/${visitId}/medication-administration/${administrationId}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Create lab sample collection
 */
export async function createLabSampleCollection(
  visitId: number,
  data: LabSampleCollectionCreate
): Promise<LabSampleCollection> {
  return apiRequest<LabSampleCollection>(`/visits/${visitId}/lab-samples/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Fetch lab sample collections for a visit
 */
export async function fetchLabSampleCollections(
  visitId: number
): Promise<LabSampleCollection[]> {
  return apiRequest<LabSampleCollection[]>(`/visits/${visitId}/lab-samples/`);
}

/**
 * Update lab sample collection
 */
export async function updateLabSampleCollection(
  visitId: number,
  collectionId: number,
  data: LabSampleCollectionCreate
): Promise<LabSampleCollection> {
  return apiRequest<LabSampleCollection>(`/visits/${visitId}/lab-samples/${collectionId}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

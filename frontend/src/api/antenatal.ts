/**
 * Antenatal Clinic Management API Client
 * 
 * Endpoints:
 * - /api/v1/antenatal/records/              - Antenatal record management
 * - /api/v1/antenatal/visits/               - Antenatal visit management
 * - /api/v1/antenatal/ultrasounds/          - Ultrasound management
 * - /api/v1/antenatal/labs/                 - Lab test management
 * - /api/v1/antenatal/medications/          - Medication management
 * - /api/v1/antenatal/outcomes/             - Delivery outcome management
 */
import { apiRequest } from '../utils/apiClient';
import {
  AntenatalRecord,
  AntenatalRecordListItem,
  AntenatalRecordCreateData,
  AntenatalRecordUpdateData,
  AntenatalRecordSummary,
  AntenatalVisit,
  AntenatalVisitCreateData,
  AntenatalUltrasound,
  AntenatalUltrasoundCreateData,
  AntenatalLab,
  AntenatalLabCreateData,
  AntenatalMedication,
  AntenatalMedicationCreateData,
  AntenatalOutcome,
  AntenatalOutcomeCreateData,
  PregnancyOutcome,
} from '../types/antenatal';

// Re-export types for convenience
export * from '../types/antenatal';

// ============================================================================
// Antenatal Record API
// ============================================================================

interface PaginatedResponse<T> {
  results: T[];
  count: number;
  next: string | null;
  previous: string | null;
}

interface RecordFilters {
  outcome?: PregnancyOutcome;
  high_risk?: boolean;
  patient?: number;
  parity?: string;
  pregnancy_type?: string;
  search?: string;
  ordering?: string;
  page?: number;
}

/**
 * Fetch antenatal records with optional filters
 */
export async function fetchAntenatalRecords(filters?: RecordFilters): Promise<AntenatalRecordListItem[]> {
  const params = new URLSearchParams();
  
  if (filters) {
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, String(value));
      }
    });
  }
  
  const queryString = params.toString();
  const url = `/antenatal/records/${queryString ? `?${queryString}` : ''}`;
  const response = await apiRequest<PaginatedResponse<AntenatalRecordListItem> | AntenatalRecordListItem[]>(url);
  
  if (response && typeof response === 'object' && 'results' in response) {
    return response.results;
  }
  return Array.isArray(response) ? response : [];
}

/**
 * Fetch a single antenatal record by ID
 */
export async function fetchAntenatalRecord(recordId: number): Promise<AntenatalRecord> {
  return apiRequest<AntenatalRecord>(`/antenatal/records/${recordId}/`);
}

/**
 * Create a new antenatal record
 */
export async function createAntenatalRecord(data: AntenatalRecordCreateData): Promise<AntenatalRecord> {
  return apiRequest<AntenatalRecord>('/antenatal/records/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Update an antenatal record
 */
export async function updateAntenatalRecord(
  recordId: number,
  data: AntenatalRecordUpdateData
): Promise<AntenatalRecord> {
  return apiRequest<AntenatalRecord>(`/antenatal/records/${recordId}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Get summary for an antenatal record
 */
export async function getAntenatalRecordSummary(recordId: number): Promise<AntenatalRecordSummary> {
  return apiRequest<AntenatalRecordSummary>(`/antenatal/records/${recordId}/summary/`);
}

/**
 * Get all visits for an antenatal record
 */
export async function getAntenatalRecordVisits(recordId: number): Promise<AntenatalVisit[]> {
  return apiRequest<AntenatalVisit[]>(`/antenatal/records/${recordId}/visits/`);
}

// ============================================================================
// Antenatal Visit API
// ============================================================================

interface VisitFilters {
  antenatal_record?: number;
  visit?: number;
  visit_type?: string;
  visit_date?: string;
  ordering?: string;
}

/**
 * Fetch antenatal visits with optional filters
 */
export async function fetchAntenatalVisits(filters?: VisitFilters): Promise<AntenatalVisit[]> {
  const params = new URLSearchParams();
  
  if (filters) {
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, String(value));
      }
    });
  }
  
  const queryString = params.toString();
  const url = `/antenatal/visits/${queryString ? `?${queryString}` : ''}`;
  const response = await apiRequest<PaginatedResponse<AntenatalVisit> | AntenatalVisit[]>(url);
  
  if (response && typeof response === 'object' && 'results' in response) {
    return response.results;
  }
  return Array.isArray(response) ? response : [];
}

/**
 * Fetch a single antenatal visit by ID
 */
export async function fetchAntenatalVisit(visitId: number): Promise<AntenatalVisit> {
  return apiRequest<AntenatalVisit>(`/antenatal/visits/${visitId}/`);
}

/**
 * Create a new antenatal visit
 */
export async function createAntenatalVisit(data: AntenatalVisitCreateData): Promise<AntenatalVisit> {
  return apiRequest<AntenatalVisit>('/antenatal/visits/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Update an antenatal visit
 */
export async function updateAntenatalVisit(
  visitId: number,
  data: Partial<AntenatalVisitCreateData>
): Promise<AntenatalVisit> {
  return apiRequest<AntenatalVisit>(`/antenatal/visits/${visitId}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Get all ultrasounds for a visit
 */
export async function getVisitUltrasounds(visitId: number): Promise<AntenatalUltrasound[]> {
  return apiRequest<AntenatalUltrasound[]>(`/antenatal/visits/${visitId}/ultrasounds/`);
}

/**
 * Get all lab tests for a visit
 */
export async function getVisitLabs(visitId: number): Promise<AntenatalLab[]> {
  return apiRequest<AntenatalLab[]>(`/antenatal/visits/${visitId}/labs/`);
}

/**
 * Get all medications for a visit
 */
export async function getVisitMedications(visitId: number): Promise<AntenatalMedication[]> {
  return apiRequest<AntenatalMedication[]>(`/antenatal/visits/${visitId}/medications/`);
}

// ============================================================================
// Antenatal Ultrasound API
// ============================================================================

/**
 * Create a new antenatal ultrasound
 */
export async function createAntenatalUltrasound(data: AntenatalUltrasoundCreateData): Promise<AntenatalUltrasound> {
  return apiRequest<AntenatalUltrasound>('/antenatal/ultrasounds/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Update an antenatal ultrasound
 */
export async function updateAntenatalUltrasound(
  ultrasoundId: number,
  data: Partial<AntenatalUltrasoundCreateData>
): Promise<AntenatalUltrasound> {
  return apiRequest<AntenatalUltrasound>(`/antenatal/ultrasounds/${ultrasoundId}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Delete an antenatal ultrasound
 */
export async function deleteAntenatalUltrasound(ultrasoundId: number): Promise<void> {
  return apiRequest<void>(`/antenatal/ultrasounds/${ultrasoundId}/`, {
    method: 'DELETE',
  });
}

// ============================================================================
// Antenatal Lab API
// ============================================================================

/**
 * Create a new antenatal lab test
 */
export async function createAntenatalLab(data: AntenatalLabCreateData): Promise<AntenatalLab> {
  return apiRequest<AntenatalLab>('/antenatal/labs/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Update an antenatal lab test
 */
export async function updateAntenatalLab(
  labId: number,
  data: Partial<AntenatalLabCreateData>
): Promise<AntenatalLab> {
  return apiRequest<AntenatalLab>(`/antenatal/labs/${labId}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Delete an antenatal lab test
 */
export async function deleteAntenatalLab(labId: number): Promise<void> {
  return apiRequest<void>(`/antenatal/labs/${labId}/`, {
    method: 'DELETE',
  });
}

// ============================================================================
// Antenatal Medication API
// ============================================================================

/**
 * Create a new antenatal medication
 */
export async function createAntenatalMedication(data: AntenatalMedicationCreateData): Promise<AntenatalMedication> {
  return apiRequest<AntenatalMedication>('/antenatal/medications/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Update an antenatal medication
 */
export async function updateAntenatalMedication(
  medicationId: number,
  data: Partial<AntenatalMedicationCreateData>
): Promise<AntenatalMedication> {
  return apiRequest<AntenatalMedication>(`/antenatal/medications/${medicationId}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Delete an antenatal medication
 */
export async function deleteAntenatalMedication(medicationId: number): Promise<void> {
  return apiRequest<void>(`/antenatal/medications/${medicationId}/`, {
    method: 'DELETE',
  });
}

// ============================================================================
// Antenatal Outcome API
// ============================================================================

/**
 * Fetch antenatal outcomes
 */
export async function fetchAntenatalOutcomes(recordId?: number): Promise<AntenatalOutcome[]> {
  const params = new URLSearchParams();
  if (recordId) {
    params.append('antenatal_record', String(recordId));
  }
  
  const queryString = params.toString();
  const url = `/antenatal/outcomes/${queryString ? `?${queryString}` : ''}`;
  const response = await apiRequest<PaginatedResponse<AntenatalOutcome> | AntenatalOutcome[]>(url);
  
  if (response && typeof response === 'object' && 'results' in response) {
    return response.results;
  }
  return Array.isArray(response) ? response : [];
}

/**
 * Fetch a single antenatal outcome by ID
 */
export async function fetchAntenatalOutcome(outcomeId: number): Promise<AntenatalOutcome> {
  return apiRequest<AntenatalOutcome>(`/antenatal/outcomes/${outcomeId}/`);
}

/**
 * Create a new antenatal outcome
 */
export async function createAntenatalOutcome(data: AntenatalOutcomeCreateData): Promise<AntenatalOutcome> {
  return apiRequest<AntenatalOutcome>('/antenatal/outcomes/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Update an antenatal outcome
 */
export async function updateAntenatalOutcome(
  outcomeId: number,
  data: Partial<AntenatalOutcomeCreateData>
): Promise<AntenatalOutcome> {
  return apiRequest<AntenatalOutcome>(`/antenatal/outcomes/${outcomeId}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

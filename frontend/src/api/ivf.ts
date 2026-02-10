/**
 * IVF Treatment Module API Client
 * 
 * Endpoints:
 * - /api/v1/ivf/cycles/                              - IVF Cycle management
 * - /api/v1/ivf/cycles/{cycleId}/stimulation/        - Ovarian stimulation records
 * - /api/v1/ivf/cycles/{cycleId}/retrieval/          - Oocyte retrieval
 * - /api/v1/ivf/cycles/{cycleId}/embryos/            - Embryo management
 * - /api/v1/ivf/cycles/{cycleId}/transfers/          - Embryo transfers
 * - /api/v1/ivf/cycles/{cycleId}/medications/        - IVF medications
 * - /api/v1/ivf/cycles/{cycleId}/consents/           - Consent management
 * - /api/v1/ivf/sperm-analyses/                      - Sperm analysis records
 * - /api/v1/ivf/outcomes/                            - IVF outcomes
 */
import { apiRequest } from '../utils/apiClient';
import {
  IVFCycle,
  IVFCycleListItem,
  IVFCycleCreateData,
  IVFCycleUpdateData,
  IVFCycleFull,
  OvarianStimulation,
  OvarianStimulationCreateData,
  OocyteRetrieval,
  OocyteRetrievalCreateData,
  SpermAnalysis,
  SpermAnalysisListItem,
  SpermAnalysisCreateData,
  Embryo,
  EmbryoListItem,
  EmbryoCreateData,
  EmbryoTransfer,
  EmbryoTransferCreateData,
  IVFMedication,
  IVFMedicationCreateData,
  IVFOutcome,
  IVFOutcomeCreateData,
  IVFConsent,
  IVFConsentCreateData,
  IVFStatistics,
  CycleStatus,
  CancellationReason,
} from '../types/ivf';

// Re-export types for convenience
export * from '../types/ivf';

// ============================================================================
// IVF Cycle API
// ============================================================================

interface PaginatedResponse<T> {
  results: T[];
  count: number;
  next: string | null;
  previous: string | null;
}

interface CycleFilters {
  status?: CycleStatus;
  cycle_type?: string;
  patient?: number;
  consent_signed?: boolean;
  search?: string;
  ordering?: string;
  page?: number;
}

/**
 * Fetch IVF cycles with optional filters
 */
export async function fetchIVFCycles(filters?: CycleFilters): Promise<IVFCycleListItem[]> {
  const params = new URLSearchParams();
  
  if (filters) {
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, String(value));
      }
    });
  }
  
  const queryString = params.toString();
  const url = `/ivf/cycles/${queryString ? `?${queryString}` : ''}`;
  const response = await apiRequest<PaginatedResponse<IVFCycleListItem> | IVFCycleListItem[]>(url);
  
  if (response && typeof response === 'object' && 'results' in response) {
    return response.results;
  }
  return Array.isArray(response) ? response : [];
}

/**
 * Fetch a single IVF cycle by ID
 */
export async function fetchIVFCycle(cycleId: number): Promise<IVFCycle> {
  return apiRequest<IVFCycle>(`/ivf/cycles/${cycleId}/`);
}

/**
 * Fetch complete IVF cycle details with all related data
 */
export async function fetchIVFCycleFull(cycleId: number): Promise<IVFCycleFull> {
  return apiRequest<IVFCycleFull>(`/ivf/cycles/${cycleId}/full_details/`);
}

/**
 * Create a new IVF cycle
 */
export async function createIVFCycle(data: IVFCycleCreateData): Promise<IVFCycle> {
  return apiRequest<IVFCycle>('/ivf/cycles/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Update an IVF cycle
 */
export async function updateIVFCycle(cycleId: number, data: IVFCycleUpdateData): Promise<IVFCycle> {
  return apiRequest<IVFCycle>(`/ivf/cycles/${cycleId}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Cancel an IVF cycle
 */
export async function cancelIVFCycle(
  cycleId: number, 
  reason: CancellationReason, 
  notes?: string
): Promise<{ message: string; cycle_id: number; status: string }> {
  return apiRequest(`/ivf/cycles/${cycleId}/cancel/`, {
    method: 'POST',
    body: JSON.stringify({ reason, notes }),
  });
}

/**
 * Sign consent for a cycle
 */
export async function signCycleConsent(
  cycleId: number,
  consentType: 'patient' | 'partner'
): Promise<{ message: string; consent_signed: boolean; partner_consent_signed: boolean }> {
  return apiRequest(`/ivf/cycles/${cycleId}/sign_consent/`, {
    method: 'POST',
    body: JSON.stringify({ consent_type: consentType }),
  });
}

/**
 * Advance cycle to next status
 */
export async function advanceCycleStatus(
  cycleId: number,
  newStatus: CycleStatus
): Promise<{ message: string; new_status: string }> {
  return apiRequest(`/ivf/cycles/${cycleId}/advance_status/`, {
    method: 'POST',
    body: JSON.stringify({ status: newStatus }),
  });
}

/**
 * Fetch IVF statistics
 */
export async function fetchIVFStatistics(
  startDate?: string,
  endDate?: string
): Promise<IVFStatistics> {
  const params = new URLSearchParams();
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  
  const queryString = params.toString();
  return apiRequest<IVFStatistics>(`/ivf/cycles/statistics/${queryString ? `?${queryString}` : ''}`);
}

// ============================================================================
// Ovarian Stimulation API
// ============================================================================

/**
 * Fetch stimulation records for a cycle
 */
export async function fetchStimulationRecords(cycleId: number): Promise<OvarianStimulation[]> {
  const response = await apiRequest<PaginatedResponse<OvarianStimulation> | OvarianStimulation[]>(
    `/ivf/cycles/${cycleId}/stimulation/`
  );
  
  if (response && typeof response === 'object' && 'results' in response) {
    return response.results;
  }
  return Array.isArray(response) ? response : [];
}

/**
 * Create a stimulation record
 */
export async function createStimulationRecord(
  cycleId: number,
  data: OvarianStimulationCreateData
): Promise<OvarianStimulation> {
  return apiRequest<OvarianStimulation>(`/ivf/cycles/${cycleId}/stimulation/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Update a stimulation record
 */
export async function updateStimulationRecord(
  cycleId: number,
  recordId: number,
  data: Partial<OvarianStimulationCreateData>
): Promise<OvarianStimulation> {
  return apiRequest<OvarianStimulation>(`/ivf/cycles/${cycleId}/stimulation/${recordId}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

// ============================================================================
// Oocyte Retrieval API
// ============================================================================

/**
 * Fetch oocyte retrieval for a cycle
 */
export async function fetchOocyteRetrieval(cycleId: number): Promise<OocyteRetrieval | null> {
  try {
    const response = await apiRequest<PaginatedResponse<OocyteRetrieval> | OocyteRetrieval[]>(
      `/ivf/cycles/${cycleId}/retrieval/`
    );
    
    if (response && typeof response === 'object' && 'results' in response) {
      return response.results[0] || null;
    }
    return Array.isArray(response) ? response[0] || null : null;
  } catch (error) {
    return null;
  }
}

/**
 * Create oocyte retrieval record
 */
export async function createOocyteRetrieval(
  cycleId: number,
  data: OocyteRetrievalCreateData
): Promise<OocyteRetrieval> {
  return apiRequest<OocyteRetrieval>(`/ivf/cycles/${cycleId}/retrieval/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Update oocyte retrieval record
 */
export async function updateOocyteRetrieval(
  cycleId: number,
  retrievalId: number,
  data: Partial<OocyteRetrievalCreateData>
): Promise<OocyteRetrieval> {
  return apiRequest<OocyteRetrieval>(`/ivf/cycles/${cycleId}/retrieval/${retrievalId}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

// ============================================================================
// Sperm Analysis API
// ============================================================================

/**
 * Fetch sperm analyses with optional filters
 */
export async function fetchSpermAnalyses(filters?: {
  patient?: number;
  cycle?: number;
  assessment?: string;
}): Promise<SpermAnalysisListItem[]> {
  const params = new URLSearchParams();
  
  if (filters) {
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, String(value));
      }
    });
  }
  
  const queryString = params.toString();
  const response = await apiRequest<PaginatedResponse<SpermAnalysisListItem> | SpermAnalysisListItem[]>(
    `/ivf/sperm-analyses/${queryString ? `?${queryString}` : ''}`
  );
  
  if (response && typeof response === 'object' && 'results' in response) {
    return response.results;
  }
  return Array.isArray(response) ? response : [];
}

/**
 * Fetch a single sperm analysis
 */
export async function fetchSpermAnalysis(analysisId: number): Promise<SpermAnalysis> {
  return apiRequest<SpermAnalysis>(`/ivf/sperm-analyses/${analysisId}/`);
}

/**
 * Create a sperm analysis
 */
export async function createSpermAnalysis(data: SpermAnalysisCreateData): Promise<SpermAnalysis> {
  return apiRequest<SpermAnalysis>('/ivf/sperm-analyses/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ============================================================================
// Embryo API
// ============================================================================

/**
 * Fetch embryos for a cycle
 */
export async function fetchEmbryos(cycleId: number): Promise<EmbryoListItem[]> {
  const response = await apiRequest<PaginatedResponse<EmbryoListItem> | EmbryoListItem[]>(
    `/ivf/cycles/${cycleId}/embryos/`
  );
  
  if (response && typeof response === 'object' && 'results' in response) {
    return response.results;
  }
  return Array.isArray(response) ? response : [];
}

/**
 * Fetch a single embryo
 */
export async function fetchEmbryo(cycleId: number, embryoId: number): Promise<Embryo> {
  return apiRequest<Embryo>(`/ivf/cycles/${cycleId}/embryos/${embryoId}/`);
}

/**
 * Create an embryo record
 */
export async function createEmbryo(cycleId: number, data: EmbryoCreateData): Promise<Embryo> {
  return apiRequest<Embryo>(`/ivf/cycles/${cycleId}/embryos/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Update an embryo record
 */
export async function updateEmbryo(
  cycleId: number,
  embryoId: number,
  data: Partial<Embryo>
): Promise<Embryo> {
  return apiRequest<Embryo>(`/ivf/cycles/${cycleId}/embryos/${embryoId}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Freeze an embryo
 */
export async function freezeEmbryo(
  cycleId: number,
  embryoId: number,
  storageLocation: string,
  strawId?: string
): Promise<{ message: string; lab_id: string; storage_location: string }> {
  return apiRequest(`/ivf/cycles/${cycleId}/embryos/${embryoId}/freeze/`, {
    method: 'POST',
    body: JSON.stringify({ storage_location: storageLocation, straw_id: strawId }),
  });
}

/**
 * Thaw an embryo
 */
export async function thawEmbryo(
  cycleId: number,
  embryoId: number,
  survived: boolean = true
): Promise<{ message: string; lab_id: string; survived: boolean }> {
  return apiRequest(`/ivf/cycles/${cycleId}/embryos/${embryoId}/thaw/`, {
    method: 'POST',
    body: JSON.stringify({ survived }),
  });
}

/**
 * Set embryo disposition
 */
export async function disposeEmbryo(
  cycleId: number,
  embryoId: number,
  disposition: string,
  notes?: string
): Promise<{ message: string; lab_id: string; disposition: string }> {
  return apiRequest(`/ivf/cycles/${cycleId}/embryos/${embryoId}/dispose/`, {
    method: 'POST',
    body: JSON.stringify({ disposition, notes }),
  });
}

// ============================================================================
// Embryo Transfer API
// ============================================================================

/**
 * Fetch embryo transfers for a cycle
 */
export async function fetchEmbryoTransfers(cycleId: number): Promise<EmbryoTransfer[]> {
  const response = await apiRequest<PaginatedResponse<EmbryoTransfer> | EmbryoTransfer[]>(
    `/ivf/cycles/${cycleId}/transfers/`
  );
  
  if (response && typeof response === 'object' && 'results' in response) {
    return response.results;
  }
  return Array.isArray(response) ? response : [];
}

/**
 * Create an embryo transfer
 */
export async function createEmbryoTransfer(
  cycleId: number,
  data: EmbryoTransferCreateData
): Promise<EmbryoTransfer> {
  return apiRequest<EmbryoTransfer>(`/ivf/cycles/${cycleId}/transfers/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ============================================================================
// IVF Medication API
// ============================================================================

/**
 * Fetch medications for a cycle
 */
export async function fetchIVFMedications(cycleId: number): Promise<IVFMedication[]> {
  const response = await apiRequest<PaginatedResponse<IVFMedication> | IVFMedication[]>(
    `/ivf/cycles/${cycleId}/medications/`
  );
  
  if (response && typeof response === 'object' && 'results' in response) {
    return response.results;
  }
  return Array.isArray(response) ? response : [];
}

/**
 * Create a medication record
 */
export async function createIVFMedication(
  cycleId: number,
  data: IVFMedicationCreateData
): Promise<IVFMedication> {
  return apiRequest<IVFMedication>(`/ivf/cycles/${cycleId}/medications/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Delete a medication record
 */
export async function deleteIVFMedication(cycleId: number, medicationId: number): Promise<void> {
  return apiRequest(`/ivf/cycles/${cycleId}/medications/${medicationId}/`, {
    method: 'DELETE',
  });
}

// ============================================================================
// IVF Outcome API
// ============================================================================

/**
 * Fetch IVF outcome for a cycle
 */
export async function fetchIVFOutcome(cycleId: number): Promise<IVFOutcome | null> {
  try {
    const response = await apiRequest<PaginatedResponse<IVFOutcome> | IVFOutcome[]>(
      `/ivf/outcomes/?cycle=${cycleId}`
    );
    
    if (response && typeof response === 'object' && 'results' in response) {
      return response.results[0] || null;
    }
    return Array.isArray(response) ? response[0] || null : null;
  } catch (error) {
    return null;
  }
}

/**
 * Create or update IVF outcome
 */
export async function createIVFOutcome(data: IVFOutcomeCreateData & { cycle: number }): Promise<IVFOutcome> {
  return apiRequest<IVFOutcome>('/ivf/outcomes/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Update IVF outcome
 */
export async function updateIVFOutcome(
  outcomeId: number,
  data: Partial<IVFOutcome>
): Promise<IVFOutcome> {
  return apiRequest<IVFOutcome>(`/ivf/outcomes/${outcomeId}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

// ============================================================================
// IVF Consent API
// ============================================================================

/**
 * Fetch consents for a cycle
 */
export async function fetchIVFConsents(cycleId: number): Promise<IVFConsent[]> {
  const response = await apiRequest<PaginatedResponse<IVFConsent> | IVFConsent[]>(
    `/ivf/cycles/${cycleId}/consents/`
  );
  
  if (response && typeof response === 'object' && 'results' in response) {
    return response.results;
  }
  return Array.isArray(response) ? response : [];
}

/**
 * Create a consent record
 */
export async function createIVFConsent(
  cycleId: number,
  data: IVFConsentCreateData
): Promise<IVFConsent> {
  return apiRequest<IVFConsent>(`/ivf/cycles/${cycleId}/consents/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Sign a consent
 */
export async function signIVFConsent(
  cycleId: number,
  consentId: number,
  witnessName?: string
): Promise<{ message: string; consent_id: number; consent_type: string }> {
  return apiRequest(`/ivf/cycles/${cycleId}/consents/${consentId}/sign/`, {
    method: 'POST',
    body: JSON.stringify({ witness_name: witnessName }),
  });
}

/**
 * Revoke a consent
 */
export async function revokeIVFConsent(
  cycleId: number,
  consentId: number,
  reason: string
): Promise<{ message: string; consent_id: number }> {
  return apiRequest(`/ivf/cycles/${cycleId}/consents/${consentId}/revoke/`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}

// ============================================================================
// Embryo Inventory API
// ============================================================================

export interface EmbryoInventoryItem {
  id: number;
  cycle_id: number;
  embryo_number: number;
  lab_id: string;
  patient_name: string;
  partner_name?: string;
  cycle_number: number;
  status: string;
  stage: string;
  grade?: string;
  freeze_date?: string;
  storage_days?: number;
  tank_location?: string;
  straw_id?: string;
  pgt_result?: string;
}

/**
 * Fetch embryo inventory (frozen embryos)
 */
export async function fetchEmbryoInventory(filters?: {
  status?: string;
  grade?: string;
  patient?: number;
}): Promise<EmbryoInventoryItem[]> {
  const params = new URLSearchParams();
  
  if (filters) {
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, String(value));
      }
    });
  }
  
  const queryString = params.toString();
  const response = await apiRequest<PaginatedResponse<EmbryoInventoryItem> | EmbryoInventoryItem[]>(
    `/ivf/embryo-inventory/${queryString ? `?${queryString}` : ''}`
  );
  
  if (response && typeof response === 'object' && 'results' in response) {
    return response.results;
  }
  return Array.isArray(response) ? response : [];
}

/**
 * Thaw an embryo from inventory
 */
export async function thawEmbryoFromInventory(
  embryoId: number,
  data: { thaw_date: string; notes?: string }
): Promise<{ message: string; embryo_id: number }> {
  return apiRequest(`/ivf/embryo-inventory/${embryoId}/thaw/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Dispose an embryo from inventory
 */
export async function disposeEmbryoFromInventory(
  embryoId: number,
  data: { reason: string; notes?: string }
): Promise<{ message: string; embryo_id: number }> {
  return apiRequest(`/ivf/embryo-inventory/${embryoId}/dispose/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ============================================================================
// IVF Patients & Visits (IVF-scoped only)
// ============================================================================

export interface IVFPatientListItem {
  id: number;
  patient_id: string;
  first_name: string;
  last_name: string;
  cycle_count: number;
}

/**
 * Fetch patients who have at least one IVF cycle (IVF patients only)
 */
export async function fetchIVFPatients(): Promise<IVFPatientListItem[]> {
  const response = await apiRequest<IVFPatientListItem[]>('/ivf/patients/');
  return Array.isArray(response) ? response : [];
}

/**
 * Fetch visits for patients who have at least one IVF cycle (IVF patient visits only)
 */
export async function fetchIVFVisits(filters?: { status?: string }): Promise<any[]> {
  const params = new URLSearchParams();
  if (filters?.status) params.append('status', filters.status);
  const query = params.toString();
  const url = query ? `/ivf/visits/?${query}` : '/ivf/visits/';
  const response = await apiRequest<any[]>(url);
  return Array.isArray(response) ? response : [];
}

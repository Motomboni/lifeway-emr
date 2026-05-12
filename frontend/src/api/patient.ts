/**
 * Patient API Client
 * 
 * Endpoints:
 * - GET    /api/v1/patients/          - List patients (with search)
 * - POST   /api/v1/patients/          - Create patient (Receptionist)
 * - GET    /api/v1/patients/{id}/     - Get patient
 * - GET    /api/v1/patients/search/?q= - Search patients
 */
import { Patient, PatientCreateData } from '../types/patient';
import { apiRequest } from '../utils/apiClient';

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface PatientListOptions {
  searchQuery?: string;
  includeInactive?: boolean;
  page?: number;
  pageSize?: number;
}

/**
 * Fetch patients (with optional search)
 * Returns paginated response - extracts results array
 */
export async function fetchPatients(searchQuery?: string): Promise<Patient[]> {
  const response = await fetchPatientsPage({ searchQuery });
  return response.results || [];
}

/**
 * Fetch one paginated page of patients.
 */
export async function fetchPatientsPage(options: PatientListOptions = {}): Promise<PaginatedResponse<Patient>> {
  const params = new URLSearchParams();
  if (options.searchQuery) params.append('search', options.searchQuery);
  if (options.includeInactive) params.append('include_inactive', 'true');
  if (options.page) params.append('page', String(options.page));
  if (options.pageSize) params.append('page_size', String(options.pageSize));

  const queryString = params.toString();
  const endpoint = queryString ? `/patients/?${queryString}` : '/patients/';
  const response = await apiRequest<PaginatedResponse<Patient> | Patient[]>(endpoint);

  // Handle both paginated and non-paginated responses
  if (Array.isArray(response)) {
    return {
      count: response.length,
      next: null,
      previous: null,
      results: response,
    };
  }

  return response;
}

/**
 * Search patients
 * Note: The search endpoint returns a plain array, not paginated
 */
export async function searchPatients(query: string, includeInactive = true): Promise<Patient[]> {
  const params = new URLSearchParams({ q: query });
  if (includeInactive) params.append('include_inactive', 'true');
  const response = await apiRequest<Patient[]>(
    `/patients/search/?${params.toString()}`
  );
  
  // Search endpoint returns plain array
  return Array.isArray(response) ? response : [];
}

/**
 * Get patient by ID
 */
export async function getPatient(patientId: number): Promise<Patient> {
  return apiRequest<Patient>(`/patients/${patientId}/`);
}

/**
 * Create a new patient (Receptionist only)
 */
export async function createPatient(patientData: PatientCreateData): Promise<Patient> {
  return apiRequest<Patient>('/patients/', {
    method: 'POST',
    body: JSON.stringify(patientData),
  });
}

/**
 * Get patients pending verification (Receptionist only)
 */
export async function getPendingVerificationPatients(): Promise<Patient[]> {
  return apiRequest<Patient[]>('/patients/pending-verification/');
}

/**
 * Verify a patient account (Receptionist only)
 */
export async function verifyPatient(patientId: number): Promise<Patient> {
  return apiRequest<Patient>(`/patients/${patientId}/verify/`, {
    method: 'POST',
  });
}

/**
 * Update patient (Receptionist only)
 */
export async function updatePatient(
  patientId: number,
  patientData: Partial<PatientCreateData>
): Promise<Patient> {
  return apiRequest<Patient>(`/patients/${patientId}/`, {
    method: 'PATCH',
    body: JSON.stringify(patientData),
  });
}

/**
 * Create portal account for existing patient (Receptionist/Admin only)
 */
export interface CreatePortalAccountData {
  email: string;
  phone?: string;
}

export interface CreatePortalAccountResponse {
  success: boolean;
  message: string;
  credentials: {
    username: string;
    temporary_password: string;
    login_url: string;
  };
  patient: {
    id: number;
    patient_id: string;
    name: string;
    portal_enabled: boolean;
  };
}

export async function createPortalAccount(
  patientId: number,
  data: CreatePortalAccountData
): Promise<CreatePortalAccountResponse> {
  return apiRequest<CreatePortalAccountResponse>(`/patients/${patientId}/create-portal/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Archive (soft-delete) patient. Admin, Receptionist, or Superuser only.
 * Per EMR rules: soft-delete only (is_active=False).
 */
export async function archivePatient(patientId: number): Promise<{ detail: string }> {
  return apiRequest<{ detail: string }>(`/patients/${patientId}/`, {
    method: 'DELETE',
  });
}

/**
 * Toggle patient portal access (Admin only)
 */
export interface TogglePortalResponse {
  success: boolean;
  message: string;
  portal_enabled: boolean;
  portal_user_active: boolean | null;
  no_change?: boolean;
}

export async function togglePortalAccess(
  patientId: number,
  enabled: boolean
): Promise<TogglePortalResponse> {
  return apiRequest<TogglePortalResponse>(`/patients/${patientId}/toggle-portal/`, {
    method: 'POST',
    body: JSON.stringify({ enabled }),
  });
}

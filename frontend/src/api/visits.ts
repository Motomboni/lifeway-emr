/**
 * Visits API Client
 * 
 * Endpoints:
 * - GET    /api/v1/visits/          - List visits
 * - POST   /api/v1/visits/          - Create visit
 * - GET    /api/v1/visits/{id}/     - Get visit
 * - POST   /api/v1/visits/{id}/close/ - Close visit (Doctor)
 */
import { apiRequest } from '../utils/apiClient';
import { Visit, VisitCreateData } from '../types/visit';

// Re-export types for convenience
export type { Visit, VisitCreateData } from '../types/visit';

export interface VisitDetails {
  id: number;
  patient: number;
  patient_name?: string;
  patient_id?: string;
  patient_details?: {
    name: string;
    age?: number;
    gender?: string;
    phone?: string;
  };
  status: string;
  payment_status: string;
  created_at: string;
}

/**
 * Fetch visit details for consultation header
 */
export async function fetchVisitDetails(visitId: string): Promise<VisitDetails> {
  return apiRequest<VisitDetails>(`/visits/${visitId}/`);
}

export interface VisitFilters {
  patient?: number;
  status?: 'OPEN' | 'CLOSED';
  payment_status?: 'UNPAID' | 'PARTIALLY_PAID' | 'PAID' | 'INSURANCE_PENDING' | 'INSURANCE_CLAIMED' | 'SETTLED';
  date_from?: string;
  date_to?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/**
 * Fetch visits (with optional filters and pagination)
 */
export async function fetchVisits(filters?: VisitFilters): Promise<Visit[] | PaginatedResponse<Visit>> {
  const params = new URLSearchParams();
  if (filters?.patient) params.append('patient', filters.patient.toString());
  if (filters?.status) params.append('status', filters.status);
  if (filters?.payment_status) params.append('payment_status', filters.payment_status);
  if (filters?.date_from) params.append('date_from', filters.date_from);
  if (filters?.date_to) params.append('date_to', filters.date_to);
  if (filters?.search) params.append('search', filters.search);
  if (filters?.page) params.append('page', filters.page.toString());
  if (filters?.page_size) params.append('page_size', filters.page_size.toString());
  
  const queryString = params.toString();
  const endpoint = queryString ? `/visits/?${queryString}` : '/visits/';
  return apiRequest<Visit[] | PaginatedResponse<Visit>>(endpoint);
}

/**
 * Get visit by ID
 */
export async function getVisit(visitId: number): Promise<Visit> {
  const endpoint = `/visits/${visitId}/`;
  return apiRequest<Visit>(endpoint);
}

/**
 * Create a new visit (Receptionist)
 */
export async function createVisit(visitData: VisitCreateData): Promise<Visit> {
  return apiRequest<Visit>('/visits/', {
    method: 'POST',
    body: JSON.stringify(visitData),
  });
}

/**
 * Close a visit (Doctor only)
 */
export async function closeVisit(visitId: number): Promise<Visit> {
  return apiRequest<Visit>(`/visits/${visitId}/close/`, {
    method: 'POST',
  });
}

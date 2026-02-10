/**
 * Insurance Provider API Client
 * 
 * Endpoints:
 * - GET /api/v1/billing/insurance-providers/ - List insurance providers
 */
import { apiRequest } from '../utils/apiClient';

export interface InsuranceProvider {
  id: number;
  name: string;
  code?: string;
  contact_person?: string;
  contact_phone?: string;
  contact_email?: string;
  is_active: boolean;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/**
 * Fetch insurance providers
 */
export async function fetchInsuranceProviders(): Promise<InsuranceProvider[]> {
  const response = await apiRequest<PaginatedResponse<InsuranceProvider> | InsuranceProvider[]>(
    '/billing/insurance-providers/'
  );
  
  // Handle both paginated and non-paginated responses
  if (Array.isArray(response)) {
    return response;
  }
  
  // Paginated response
  return response.results || [];
}


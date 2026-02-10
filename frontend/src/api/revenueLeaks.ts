/**
 * API client functions for Revenue Leak Detection.
 */
import { apiRequest } from '../utils/apiClient';

// Types
export interface LeakRecord {
  id: number;
  entity_type: string;
  entity_type_display: string;
  entity_id: number;
  service_code: string;
  service_name: string;
  estimated_amount: string;
  visit: number;
  visit_id?: number;
  visit_patient_name?: string;
  detected_at: string;
  resolved_at: string | null;
  resolved_by: number | null;
  resolved_by_name: string | null;
  resolution_notes: string;
  is_resolved: boolean;
  detection_context: Record<string, any>;
}

export interface DailyAggregation {
  date: string;
  total_leaks: number;
  total_amount: string;
  by_entity_type: Record<string, { count: number; amount: string }>;
}

export interface LeakSummary {
  total_leaks: number;
  total_amount: string;
  resolved_count: number;
  unresolved_count: number;
  by_entity_type: Record<string, { count: number; amount: string }>;
}

/**
 * Get all revenue leaks with optional filters.
 */
export const getRevenueLeaks = async (params?: {
  is_resolved?: boolean;
  entity_type?: string;
  start_date?: string;
  end_date?: string;
}): Promise<LeakRecord[]> => {
  const queryParams = new URLSearchParams();
  
  if (params?.is_resolved !== undefined) {
    queryParams.append('resolved', params.is_resolved.toString());
  }
  if (params?.entity_type) {
    queryParams.append('entity_type', params.entity_type);
  }
  if (params?.start_date) {
    queryParams.append('date_from', params.start_date);
  }
  if (params?.end_date) {
    queryParams.append('date_to', params.end_date);
  }
  
  const queryString = queryParams.toString();
  const url = queryString ? `/billing/leaks/?${queryString}` : '/billing/leaks/';
  
  const data = await apiRequest<any>(url);
  if (Array.isArray(data)) {
    return data as LeakRecord[];
  }
  if (data && Array.isArray(data.results)) {
    return data.results as LeakRecord[];
  }
  return [];
};

/**
 * Get a single revenue leak by ID.
 */
export const getRevenueLeak = async (id: number): Promise<LeakRecord> => {
  return apiRequest<LeakRecord>(`/billing/leaks/${id}/`);
};

/**
 * Get daily aggregation of revenue leaks.
 */
export const getDailyAggregation = async (params?: {
  start_date?: string;
  end_date?: string;
}): Promise<DailyAggregation[]> => {
  const queryParams = new URLSearchParams();
  
  if (params?.start_date) {
    queryParams.append('start_date', params.start_date);
  }
  if (params?.end_date) {
    queryParams.append('end_date', params.end_date);
  }
  
  const queryString = queryParams.toString();
  const url = queryString 
    ? `/billing/leaks/daily_aggregation/?${queryString}`
    : '/billing/leaks/daily_aggregation/';
  
  return apiRequest<DailyAggregation[]>(url);
};

/**
 * Get summary of revenue leaks.
 */
export const getLeakSummary = async (params?: {
  start_date?: string;
  end_date?: string;
}): Promise<LeakSummary> => {
  const queryParams = new URLSearchParams();
  
  if (params?.start_date) {
    queryParams.append('date_from', params.start_date);
  }
  if (params?.end_date) {
    queryParams.append('date_to', params.end_date);
  }
  
  const queryString = queryParams.toString();
  const url = queryString 
    ? `/billing/leaks/summary/?${queryString}`
    : '/billing/leaks/summary/';
  
  return apiRequest<LeakSummary>(url);
};

/**
 * Resolve a revenue leak.
 */
export const resolveLeak = async (
  id: number,
  resolutionNotes: string
): Promise<LeakRecord> => {
  return apiRequest<LeakRecord>(`/billing/leaks/${id}/resolve/`, {
    method: 'POST',
    body: JSON.stringify({ resolution_notes: resolutionNotes }),
    headers: {
      'Content-Type': 'application/json',
    },
  });
};

/**
 * Trigger leak detection for all entities.
 */
export const detectAllLeaks = async (): Promise<{ detected: number }> => {
  return apiRequest<{ detected: number }>('/billing/leaks/detect_all/', {
    method: 'POST',
  });
};


/**
 * API client functions for End-of-Day Reconciliation.
 */
import { apiRequest } from '../utils/apiClient';

// Types
export interface EndOfDayReconciliation {
  id: number;
  reconciliation_date: string;
  status: string;
  status_display: string;
  total_revenue: string;
  total_cash: string;
  total_wallet: string;
  total_paystack: string;
  total_hmo: string;
  total_insurance: string;
  total_outstanding: string;
  outstanding_visits_count: number;
  revenue_leaks_detected: number;
  revenue_leaks_amount: string;
  total_visits: number;
  active_visits_closed: number;
  has_mismatches: boolean;
  mismatch_details: Record<string, any>;
  prepared_by: number;
  prepared_by_name: string;
  reviewed_by: number | null;
  reviewed_by_name: string | null;
  finalized_by: number | null;
  finalized_by_name: string | null;
  prepared_at: string;
  reviewed_at: string | null;
  finalized_at: string | null;
  notes: string;
  reconciliation_details: Record<string, any>;
  payment_method_breakdown: Record<string, number>;
  summary: Record<string, any>;
}

export interface ReconciliationSummary {
  total_reconciliations: number;
  total_revenue: number;
  total_cash: number;
  total_wallet: number;
  total_paystack: number;
  total_hmo: number;
  total_insurance: number;
  total_outstanding: number;
  total_revenue_leaks: number;
}

/**
 * Create a new reconciliation.
 */
export const createReconciliation = async (data?: {
  reconciliation_date?: string;
  close_active_visits?: boolean;
}): Promise<EndOfDayReconciliation> => {
  return apiRequest<EndOfDayReconciliation>('/billing/reconciliation/', {
    method: 'POST',
    body: JSON.stringify(data || {}),
    headers: {
      'Content-Type': 'application/json',
    },
  });
};

/**
 * Get reconciliation for today.
 */
export const getTodayReconciliation = async (): Promise<EndOfDayReconciliation | null> => {
  try {
    return await apiRequest<EndOfDayReconciliation>('/billing/reconciliation/today/');
  } catch (error: any) {
    if (error.status === 404) {
      return null;
    }
    throw error;
  }
};

/**
 * Get reconciliation by ID.
 */
export const getReconciliation = async (id: number): Promise<EndOfDayReconciliation> => {
  return apiRequest<EndOfDayReconciliation>(`/billing/reconciliation/${id}/`);
};

/**
 * Finalize reconciliation.
 */
export const finalizeReconciliation = async (
  id: number,
  notes?: string
): Promise<EndOfDayReconciliation> => {
  return apiRequest<EndOfDayReconciliation>(`/billing/reconciliation/${id}/finalize/`, {
    method: 'POST',
    body: JSON.stringify({ notes: notes || '' }),
    headers: {
      'Content-Type': 'application/json',
    },
  });
};

/**
 * Refresh reconciliation calculations.
 */
export const refreshReconciliation = async (id: number): Promise<EndOfDayReconciliation> => {
  return apiRequest<EndOfDayReconciliation>(`/billing/reconciliation/${id}/refresh/`, {
    method: 'POST',
  });
};

/**
 * Get reconciliation summary.
 */
export const getReconciliationSummary = async (params?: {
  start_date?: string;
  end_date?: string;
}): Promise<ReconciliationSummary> => {
  const queryParams = new URLSearchParams();
  
  if (params?.start_date) {
    queryParams.append('start_date', params.start_date);
  }
  if (params?.end_date) {
    queryParams.append('end_date', params.end_date);
  }
  
  const queryString = queryParams.toString();
  const url = queryString 
    ? `/billing/reconciliation/summary/?${queryString}`
    : '/billing/reconciliation/summary/';
  
  return apiRequest<ReconciliationSummary>(url);
};


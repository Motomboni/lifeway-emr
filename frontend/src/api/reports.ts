/**
 * API client functions for Reports & Analytics.
 */
import { apiRequest } from '../utils/apiClient';

// Types
export interface ReportSummary {
  total_revenue: number;
  total_visits: number;
  total_patients: number;
  revenue_by_method: Record<string, number>;
  visits_by_status: Record<string, number>;
  revenue_trend: Array<{ date: string; revenue: number }>;
  visits_trend?: Array<{ date: string; visits: number }>;
  top_services?: Array<{ service_name: string; count: number; revenue: number }>;
}

/**
 * Get reports summary for date range.
 */
export const getReportsSummary = async (
  startDate: string,
  endDate: string
): Promise<ReportSummary> => {
  return apiRequest<ReportSummary>(
    `/reports/summary/?date_from=${startDate}&date_to=${endDate}`
  );
};

/**
 * Get revenue by payment method.
 */
export const getRevenueByMethod = async (
  startDate: string,
  endDate: string
): Promise<Record<string, number>> => {
  return apiRequest<Record<string, number>>(
    `/reports/revenue-by-method/?date_from=${startDate}&date_to=${endDate}`
  );
};

/**
 * Get revenue trend.
 */
export const getRevenueTrend = async (
  startDate: string,
  endDate: string
): Promise<Array<{ date: string; revenue: number }>> => {
  return apiRequest<Array<{ date: string; revenue: number }>>(
    `/reports/revenue-trend/?date_from=${startDate}&date_to=${endDate}`
  );
};

/**
 * Get visits by status.
 */
export const getVisitsByStatus = async (
  startDate: string,
  endDate: string
): Promise<Record<string, number>> => {
  return apiRequest<Record<string, number>>(
    `/reports/visits-by-status/?date_from=${startDate}&date_to=${endDate}`
  );
};

async function downloadRegulatoryCsv(path: string, filename: string): Promise<void> {
  const { getAuthToken } = await import('../utils/apiClient');
  const token = getAuthToken();
  const orgId = localStorage.getItem('organization_id');
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (orgId) headers['X-Organization-Id'] = orgId;

  const base = import.meta.env.VITE_API_URL || '/api/v1';
  const response = await fetch(`${base}${path}`, { headers });
  if (!response.ok) {
    throw new Error('Failed to download regulatory export');
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export async function downloadMohSummaryCsv(startDate: string, endDate: string): Promise<void> {
  const qs = new URLSearchParams({ format: 'csv', start_date: startDate, end_date: endDate });
  await downloadRegulatoryCsv(`/reports/regulatory/moh/?${qs.toString()}`, 'moh-summary.csv');
}

export async function downloadDhis2ExportCsv(startDate: string, endDate: string): Promise<void> {
  const qs = new URLSearchParams({ start_date: startDate, end_date: endDate });
  await downloadRegulatoryCsv(`/reports/regulatory/dhis2/?${qs.toString()}`, 'dhis2-export.csv');
}

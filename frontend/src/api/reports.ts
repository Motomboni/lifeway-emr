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

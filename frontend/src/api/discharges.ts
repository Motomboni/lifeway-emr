/**
 * API client for Discharge Summaries.
 */
import { apiRequest } from '../utils/apiClient';
import { DischargeSummary, DischargeSummaryCreate } from '../types/discharges';

/**
 * Fetch discharge summary for a visit
 */
export async function fetchDischargeSummary(visitId: number): Promise<DischargeSummary | null> {
  try {
    const data = await apiRequest<DischargeSummary[]>(
      `/visits/${visitId}/discharge-summaries/`
    );
    // Discharge summary is OneToOne, so return first item or null
    return Array.isArray(data) && data.length > 0 ? data[0] : null;
  } catch (error: any) {
    // 404 means no discharge summary exists yet
    if (error.status === 404) {
      return null;
    }
    throw error;
  }
}

/**
 * Create a discharge summary
 */
export async function createDischargeSummary(
  visitId: number,
  data: DischargeSummaryCreate
): Promise<DischargeSummary> {
  return apiRequest<DischargeSummary>(`/visits/${visitId}/discharge-summaries/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Export discharge summary as text
 */
export async function exportDischargeSummaryAsText(
  visitId: number,
  dischargeSummaryId: number
): Promise<Blob> {
  const response = await fetch(
    `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/visits/${visitId}/discharge-summaries/${dischargeSummaryId}/export/text/`,
    {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
      },
    }
  );
  
  if (!response.ok) {
    throw new Error('Failed to export discharge summary');
  }
  
  return response.blob();
}

/**
 * Export discharge summary as HTML
 */
export async function exportDischargeSummaryAsHTML(
  visitId: number,
  dischargeSummaryId: number
): Promise<Blob> {
  const response = await fetch(
    `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/visits/${visitId}/discharge-summaries/${dischargeSummaryId}/export/html/`,
    {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
      },
    }
  );
  
  if (!response.ok) {
    throw new Error('Failed to export discharge summary');
  }
  
  return response.blob();
}

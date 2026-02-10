/**
 * API client functions for Radiology (PACS-lite integration).
 */
import { apiRequest } from '../utils/apiClient';
import type { RadiologyOrder, RadiologyResult } from '../types/radiology';

// Types
export interface RadiologyStudy {
  id: number;
  study_uid: string;
  study_date: string;
  description: string;
  radiology_order: number;
  created_at: string;
  updated_at: string;
}

export interface RadiologySeries {
  id: number;
  series_uid: string;
  series_number: number;
  modality: string;
  body_part: string;
  description: string;
  study: number;
  created_at: string;
  updated_at: string;
}

export interface RadiologyImage {
  id: number;
  image_uid: string;
  filename: string;
  file_size: number;
  mime_type: string;
  checksum: string;
  instance_number: number;
  series: number;
  image_url?: string;
  signed_url?: string;
  created_at: string;
  updated_at: string;
}

export interface StudyImagesResponse {
  study: RadiologyStudy;
  series: Array<{
    id: number;
    series_uid: string;
    series_number: number;
    modality: string;
    body_part: string;
    description: string;
    images: RadiologyImage[];
  }>;
}

/**
 * Get study by ID.
 */
export const getStudy = async (studyId: number): Promise<RadiologyStudy> => {
  return apiRequest<RadiologyStudy>(`/radiology/studies/${studyId}/`);
};

/**
 * Get study images grouped by series.
 */
export const getStudyImages = async (studyId: number): Promise<StudyImagesResponse> => {
  return apiRequest<StudyImagesResponse>(`/radiology/studies/${studyId}/images/`);
};

/**
 * Get viewer URL for a study.
 */
export const getStudyViewerUrl = async (studyId: number): Promise<{ viewer_url: string }> => {
  return apiRequest<{ viewer_url: string }>(`/radiology/studies/${studyId}/viewer-url/`);
};

/**
 * Get image signed URL.
 */
export const getImageUrl = async (imageId: number): Promise<{ image_url: string }> => {
  return apiRequest<{ image_url: string }>(`/radiology/images/${imageId}/url/`);
};

/**
 * Fetch radiology orders for a visit.
 */
export const fetchRadiologyOrders = async (visitId: string): Promise<RadiologyOrder[]> => {
  const response = await apiRequest<any>(`/visits/${visitId}/radiology/`);
  return Array.isArray(response) ? response : (response?.results || []);
};

/**
 * Create a radiology order.
 * Note: visit_id should be in the URL path, not in the data.
 */
export const createRadiologyOrder = async (visitId: number, data: {
  consultation?: number;
  study_type: string;
  study_code?: string;
  clinical_indication?: string;
  instructions?: string;
}): Promise<RadiologyOrder> => {
  return apiRequest<RadiologyOrder>(`/visits/${visitId}/radiology/`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers: {
      'Content-Type': 'application/json',
    },
  });
};

/**
 * Fetch radiology results for a visit.
 */
export const fetchRadiologyResults = async (visitId: string): Promise<RadiologyResult[]> => {
  const response = await apiRequest<any>(`/visits/${visitId}/radiology/results/`);
  return Array.isArray(response) ? response : (response?.results || []);
};

/**
 * Update a radiology request with a report (for Radiology Tech).
 * Note: Reports are stored directly on RadiologyRequest, not as separate RadiologyResult.
 */
export const updateRadiologyReport = async (visitId: number, requestId: number, data: {
  report: string;
  finding_flag?: 'NORMAL' | 'ABNORMAL' | 'CRITICAL';
  image_count?: number;
}): Promise<RadiologyOrder> => {
  return apiRequest<RadiologyOrder>(`/visits/${visitId}/radiology/${requestId}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
    headers: {
      'Content-Type': 'application/json',
    },
  });
};

/**
 * AI-assisted draft for radiology report (Service Catalog).
 * POST /visits/{visitId}/radiology/{requestId}/draft-report/
 */
export const draftRadiologyReport = async (
  visitId: number,
  requestId: number,
  data: { study_type: string; clinical_indication: string }
): Promise<{ draft: string }> => {
  return apiRequest<{ draft: string }>(
    `/visits/${visitId}/radiology/${requestId}/draft-report/`,
    {
      method: 'POST',
      body: JSON.stringify(data),
      headers: { 'Content-Type': 'application/json' },
    }
  );
};

/**
 * Create a radiology result — DISABLED for Service Catalog.
 * RadiologyResult (POST /visits/{visitId}/radiology/results/) is legacy-only
 * (RadiologyOrder + RadiologyResult). Service Catalog orders use RadiologyRequest;
 * report via updateRadiologyReport() (PATCH on the request).
 * Do not call this for any order created via Service Catalog.
 */
export function createRadiologyResult(_visitId: number, _data: {
  radiology_order: number;
  report: string;
  finding_flag: 'NORMAL' | 'ABNORMAL' | 'CRITICAL';
  image_count?: number;
}): Promise<RadiologyResult> {
  return Promise.reject(
    new Error(
      'createRadiologyResult is disabled for Service Catalog. Use updateRadiologyReport (PATCH on the radiology request) to post reports.'
    )
  );
}

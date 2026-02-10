/**
 * API client functions for Radiology Image Upload & Sync.
 */
import { apiRequest } from '../utils/apiClient';

// Types
export interface ImageUploadSession {
  session_id: string;
  radiology_request_id: number;
  file_name: string;
  file_size: number;
  content_type: string;
  status: string;
  status_display: string;
  bytes_uploaded: number;
  upload_progress_percent: number;
  retry_count: number;
  max_retries: number;
  error_message: string;
  error_code: string;
  server_ack_received: boolean;
  server_ack_at: string | null;
  server_image_id: number | null;
  metadata_uploaded: boolean;
  metadata_uploaded_at: string | null;
  binary_uploaded: boolean;
  binary_uploaded_at: string | null;
  actor_name: string | null;
  created_at: string;
  updated_at: string;
  metadata: Record<string, any>;
}

export interface RadiologyOrder {
  id: number;
  visit: number;
  study_type: string;
  patient_name?: string;
}

/**
 * Get all upload sessions with optional filters.
 * 
 * Note: The API endpoint is visit-scoped, but we need a global view.
 * This combines pending and failed endpoints to get all active sessions.
 */
export const getUploadSessions = async (params?: {
  radiology_request_id?: number;
  status?: string;
}): Promise<ImageUploadSession[]> => {
  // If specific status filter, use appropriate endpoint
  if (params?.status === 'FAILED') {
    return getFailedUploads(params?.radiology_request_id);
  }
  
  // Default: get all active (pending + failed)
  const [pending, failed] = await Promise.all([
    getPendingUploads(params?.radiology_request_id).catch(() => []),
    getFailedUploads(params?.radiology_request_id).catch(() => []),
  ]);
  
  // Combine and deduplicate
  const allSessions = [...pending, ...failed];
  const uniqueSessions = Array.from(
    new Map(allSessions.map(s => [s.session_id, s])).values()
  );
  
  return uniqueSessions;
};

/**
 * Get pending upload sessions.
 */
export const getPendingUploads = async (
  radiologyOrderId?: number
): Promise<ImageUploadSession[]> => {
  const params = radiologyOrderId 
    ? `?radiology_request_id=${radiologyOrderId}`
    : '';
  const url = params 
    ? `/radiology/upload-sessions/pending/?${params.replace('?', '')}`
    : '/radiology/upload-sessions/pending/';
  return apiRequest<ImageUploadSession[]>(url);
};

/**
 * Get failed upload sessions.
 */
export const getFailedUploads = async (
  radiologyOrderId?: number
): Promise<ImageUploadSession[]> => {
  const params = radiologyOrderId 
    ? `?radiology_request_id=${radiologyOrderId}`
    : '';
  const url = params 
    ? `/radiology/upload-sessions/failed/?${params.replace('?', '')}`
    : '/radiology/upload-sessions/failed/';
  return apiRequest<ImageUploadSession[]>(url);
};

/**
 * Retry a failed upload session.
 */
export const retryUpload = async (sessionId: string): Promise<ImageUploadSession> => {
  return apiRequest<ImageUploadSession>(
    `/radiology/upload-sessions/${sessionId}/retry/`,
    {
      method: 'POST',
    }
  );
};

/**
 * Get a single upload session.
 */
export const getUploadSession = async (sessionId: string): Promise<ImageUploadSession> => {
  return apiRequest<ImageUploadSession>(
    `/radiology/upload-sessions/${sessionId}/`
  );
};

/**
 * Get radiology order details.
 */
/**
 * Get radiology order by ID.
 * Note: This requires a visit_id. If you have the visit_id, use the visit-scoped endpoint.
 */
export const getRadiologyOrder = async (visitId: number, orderId: number): Promise<RadiologyOrder> => {
  return apiRequest<RadiologyOrder>(`/visits/${visitId}/radiology/${orderId}/`);
};

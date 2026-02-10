/**
 * API client functions for Image Upload Sessions.
 */
import { apiRequest } from '../utils/apiClient';

// Types
export interface ImageUploadSession {
  id: number;
  session_uuid: string;
  radiology_request_id: number;
  device_id?: string;
  device_info?: Record<string, any>;
  status: 'QUEUED' | 'UPLOADING' | 'SYNCED' | 'FAILED' | 'PARTIAL';
  total_images: number;
  images_uploaded: number;
  images_failed: number;
  progress_percentage: number;
  is_complete: boolean;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  created_by_name?: string;
  upload_items?: ImageUploadItem[];
}

export interface ImageUploadItem {
  id: number;
  sequence_number: number;
  upload_status: 'PENDING' | 'METADATA_UPLOADED' | 'BINARY_UPLOADED' | 'ACK_RECEIVED' | 'FAILED';
  error_message?: string;
  metadata_uuid: string;
  metadata_status: string;
  created_at: string;
  updated_at: string;
}

export interface CreateSessionData {
  session_uuid: string;
  radiology_order: number;
  device_id?: string;
  device_info?: Record<string, any>;
  total_images: number;
}

export interface UploadMetadataData {
  image_uuid: string;
  filename: string;
  file_size: number;
  mime_type: string;
  checksum: string;
  image_metadata?: Record<string, any>;
  sequence_number: number;
}

/**
 * Create a new upload session (idempotent).
 */
export const createUploadSession = async (
  data: CreateSessionData
): Promise<ImageUploadSession> => {
  return apiRequest<ImageUploadSession>('/radiology/sessions/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

/**
 * Get upload session by ID.
 */
export const getUploadSession = async (sessionId: number): Promise<ImageUploadSession> => {
  return apiRequest<ImageUploadSession>(`/radiology/sessions/${sessionId}/`);
};

/**
 * Get upload session status.
 */
export const getUploadSessionStatus = async (sessionId: number): Promise<ImageUploadSession> => {
  return apiRequest<ImageUploadSession>(`/radiology/sessions/${sessionId}/status/`);
};

/**
 * Upload metadata for an image (idempotent).
 */
export const uploadMetadata = async (
  sessionId: number,
  data: UploadMetadataData
): Promise<{ metadata: any; upload_item: ImageUploadItem }> => {
  return apiRequest(`/radiology/sessions/${sessionId}/upload-metadata/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

/**
 * Upload binary data for an image (idempotent).
 */
export const uploadBinary = async (
  sessionId: number,
  imageUuid: string,
  file: File
): Promise<{ detail: string; image: { id: number; file_key: string } }> => {
  const formData = new FormData();
  formData.append('image_uuid', imageUuid);
  formData.append('file', file);
  
  return apiRequest(`/radiology/sessions/${sessionId}/upload-binary/`, {
    method: 'POST',
    body: formData,
    // Don't set Content-Type header, let browser set it with boundary
    headers: {},
  });
};

/**
 * Acknowledge successful upload (idempotent).
 */
export const acknowledgeUpload = async (
  sessionId: number,
  imageUuid: string
): Promise<{ detail: string }> => {
  return apiRequest(`/radiology/sessions/${sessionId}/acknowledge/`, {
    method: 'POST',
    body: JSON.stringify({ image_uuid: imageUuid }),
  });
};

/**
 * List upload sessions for a radiology order.
 */
export const listUploadSessions = async (
  radiologyOrderId?: number
): Promise<ImageUploadSession[]> => {
  const params = radiologyOrderId ? `?radiology_request_id=${radiologyOrderId}` : '';
  return apiRequest<ImageUploadSession[]>(`/radiology/sessions/${params}`);
};


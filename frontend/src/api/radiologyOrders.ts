/**
 * API client functions for Radiology Orders.
 */
import { apiRequest } from '../utils/apiClient';

export interface RadiologyOrder {
  id: number;
  visit: number;
  consultation?: number;
  study_type: string;
  status: string;
  patient_name?: string;
  study_id?: number;
  studies?: Array<{ id: number; study_uid: string }>;
  created_at: string;
  updated_at: string;
}

/**
 * Get radiology order by ID.
 * Note: This requires a visit_id. If you have the visit_id, use the visit-scoped endpoint.
 * Otherwise, this will need to be updated to include visit_id in the path.
 */
export const getRadiologyOrder = async (visitId: number, orderId: number): Promise<RadiologyOrder> => {
  return apiRequest<RadiologyOrder>(`/visits/${visitId}/radiology/${orderId}/`);
};


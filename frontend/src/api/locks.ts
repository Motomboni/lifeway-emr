/**
 * API client functions for Explainable Lock System.
 */
import { apiRequest } from '../utils/apiClient';

// Types
export interface LockResult {
  is_locked: boolean;
  reason_code: string;
  human_readable_message: string;
  details?: Record<string, any>;
  unlock_actions?: string[];
}

/**
 * Evaluate lock for an action.
 */
export const evaluateLock = async (
  actionType: string,
  params: Record<string, any>
): Promise<LockResult> => {
  return apiRequest<LockResult>('/locks/evaluate/', {
    method: 'POST',
    body: JSON.stringify({
      action_type: actionType,
      ...params,
    }),
    headers: {
      'Content-Type': 'application/json',
    },
  });
};

/**
 * Check if consultation is locked for a visit.
 */
export const checkConsultationLock = async (visitId: number): Promise<LockResult> => {
  return apiRequest<LockResult>(`/locks/consultation/?visit_id=${visitId}`);
};

/**
 * Check if radiology upload is locked.
 */
export const checkRadiologyUploadLock = async (
  radiologyOrderId: number
): Promise<LockResult> => {
  return apiRequest<LockResult>(
    `/locks/radiology_upload/?radiology_order_id=${radiologyOrderId}`
  );
};

/**
 * Check if drug dispense is locked.
 */
export const checkDrugDispenseLock = async (prescriptionId: number): Promise<LockResult> => {
  return apiRequest<LockResult>(`/locks/drug_dispense/?prescription_id=${prescriptionId}`);
};

/**
 * Check if lab order is locked.
 */
export const checkLabOrderLock = async (
  visitId: number,
  consultationId?: number
): Promise<LockResult> => {
  const params = consultationId
    ? `visit_id=${visitId}&consultation_id=${consultationId}`
    : `visit_id=${visitId}`;
  return apiRequest<LockResult>(`/locks/lab_order/?${params}`);
};

/**
 * Check if lab result posting is locked.
 */
export const checkLabResultPostLock = async (labOrderId: number): Promise<LockResult> => {
  return apiRequest<LockResult>(`/locks/lab_result_post/?lab_order_id=${labOrderId}`);
};

/**
 * Check if radiology report posting is locked.
 */
export const checkRadiologyReportLock = async (
  radiologyOrderId: number
): Promise<LockResult> => {
  return apiRequest<LockResult>(
    `/locks/radiology_report/?radiology_order_id=${radiologyOrderId}`
  );
};

/**
 * Check if radiology viewing is locked.
 */
export const checkRadiologyViewLock = async (
  radiologyOrderId: number
): Promise<LockResult> => {
  return apiRequest<LockResult>(`/locks/radiology_view/?radiology_order_id=${radiologyOrderId}`);
};

/**
 * Check if procedure is locked.
 */
export const checkProcedureLock = async (
  visitId: number,
  consultationId?: number
): Promise<LockResult> => {
  const params = consultationId
    ? `visit_id=${visitId}&consultation_id=${consultationId}`
    : `visit_id=${visitId}`;
  return apiRequest<LockResult>(`/locks/procedure/?${params}`);
};


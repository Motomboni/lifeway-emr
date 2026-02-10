/**
 * TypeScript types for Radiology Orders and Results
 */

// RadiologyRequest (from Service Catalog) - Modern approach
export interface RadiologyOrder {
  id: number;
  visit_id: number;
  consultation_id: number;
  study_type: string;  // e.g., "Chest X-Ray PA", "CT Scan Head"
  study_code: string;  // e.g., "RAD-XRAY-CHEST"
  clinical_indication: string;
  instructions: string;
  status: 'PENDING' | 'COMPLETED';
  report?: string;
  report_date?: string;
  finding_flag?: 'NORMAL' | 'ABNORMAL' | 'CRITICAL';
  image_count?: number;
  image_metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
  ordered_by: number;
  reported_by?: number;
}

export interface RadiologyOrderCreateData {
  consultation?: number;
  study_type: string;
  study_code?: string;
  clinical_indication?: string;
  instructions?: string;
}

export interface RadiologyResult {
  id: number;
  /** Backend returns radiology_order_id (RadiologyOrder system) */
  radiology_order_id?: number;
  /** Legacy / alternate field name */
  radiology_request_id?: number;
  report: string;
  finding_flag: 'NORMAL' | 'ABNORMAL' | 'CRITICAL';
  image_count: number;
  image_metadata?: Record<string, any>;
  reported_by: number;
  reported_at: string;
}

export interface RadiologyResultCreateData {
  radiology_request: number;  // Updated to match RadiologyRequest system
  report: string;
  finding_flag?: 'NORMAL' | 'ABNORMAL' | 'CRITICAL';
  image_count?: number;
  image_metadata?: Record<string, any>;
}

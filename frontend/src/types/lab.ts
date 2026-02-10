/**
 * TypeScript types for Lab Orders and Results
 */

export interface LabOrder {
  id: number;
  visit_id: number;
  consultation: number;
  tests_requested: string[] | any; // JSON array
  clinical_indication?: string;
  status: 'ORDERED' | 'SAMPLE_COLLECTED' | 'RESULT_READY';
  created_at: string;
  ordered_by: number;
}

export interface LabOrderCreateData {
  consultation: number;
  tests_requested: string[];
  clinical_indication?: string;
}

export interface LabResult {
  id: number;
  lab_order_id: number;
  result_data: string;
  abnormal_flag: 'NORMAL' | 'ABNORMAL' | 'CRITICAL';
  recorded_by: number;
  recorded_at: string;
}

export interface LabResultCreateData {
  lab_order: number;
  result_data: string;
  abnormal_flag?: 'NORMAL' | 'ABNORMAL' | 'CRITICAL';
}

/**
 * Type definitions for Discharge Summaries.
 */

export type DischargeCondition = 
  | 'STABLE'
  | 'IMPROVED'
  | 'UNCHANGED'
  | 'DETERIORATED'
  | 'CRITICAL';

export type DischargeDisposition = 
  | 'HOME'
  | 'TRANSFER'
  | 'AMA'
  | 'EXPIRED'
  | 'OTHER';

export interface DischargeSummary {
  id: number;
  visit_id: number;
  consultation_id: number;
  patient_id: number;
  patient_name: string;
  chief_complaint: string;
  admission_date: string;
  discharge_date: string;
  diagnosis: string;
  procedures_performed: string;
  treatment_summary: string;
  medications_on_discharge: string;
  follow_up_instructions: string;
  condition_at_discharge: DischargeCondition;
  discharge_disposition: DischargeDisposition;
  created_by: number;
  created_by_name: string;
  created_at: string;
  updated_at: string;
}

export interface DischargeSummaryCreate {
  consultation: number;
  chief_complaint: string;
  admission_date: string;
  discharge_date: string;
  diagnosis: string;
  procedures_performed?: string;
  treatment_summary: string;
  medications_on_discharge?: string;
  follow_up_instructions: string;
  condition_at_discharge: DischargeCondition;
  discharge_disposition: DischargeDisposition;
}

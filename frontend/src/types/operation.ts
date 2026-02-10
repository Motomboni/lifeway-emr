/**
 * Operation Notes Types
 */

export type OperationType =
  | 'MAJOR_SURGERY'
  | 'MINOR_SURGERY'
  | 'ENDOSCOPIC'
  | 'LAPAROSCOPIC'
  | 'DIAGNOSTIC'
  | 'THERAPEUTIC'
  | 'OTHER';

export type AnesthesiaType =
  | 'GENERAL'
  | 'REGIONAL'
  | 'LOCAL'
  | 'SEDATION'
  | 'NONE'
  | 'OTHER';

export interface OperationNote {
  id: number;
  visit: number;
  consultation: number;
  surgeon: number;
  surgeon_name?: string;
  assistant_surgeon?: number | null;
  assistant_surgeon_name?: string | null;
  anesthetist?: number | null;
  anesthetist_name?: string | null;
  operation_type: OperationType;
  operation_name: string;
  preoperative_diagnosis: string;
  postoperative_diagnosis?: string;
  indication: string;
  anesthesia_type: AnesthesiaType;
  anesthesia_notes?: string;
  procedure_description: string;
  findings?: string;
  technique?: string;
  complications?: string;
  estimated_blood_loss?: string;
  specimens_sent?: string;
  postoperative_plan?: string;
  postoperative_instructions?: string;
  operation_date: string;
  operation_duration_minutes?: number | null;
  patient_name?: string;
  created_at: string;
  updated_at: string;
}

export interface OperationNoteCreateData {
  consultation: number;
  assistant_surgeon?: number | null;
  anesthetist?: number | null;
  operation_type: OperationType;
  operation_name: string;
  preoperative_diagnosis: string;
  postoperative_diagnosis?: string;
  indication: string;
  anesthesia_type: AnesthesiaType;
  anesthesia_notes?: string;
  procedure_description: string;
  findings?: string;
  technique?: string;
  complications?: string;
  estimated_blood_loss?: string;
  specimens_sent?: string;
  postoperative_plan?: string;
  postoperative_instructions?: string;
  operation_date: string;
  operation_duration_minutes?: number | null;
}

export interface OperationNoteUpdateData extends Partial<OperationNoteCreateData> {}

export const OPERATION_TYPE_OPTIONS: { value: OperationType; label: string }[] = [
  { value: 'MAJOR_SURGERY', label: 'Major Surgery' },
  { value: 'MINOR_SURGERY', label: 'Minor Surgery' },
  { value: 'ENDOSCOPIC', label: 'Endoscopic Procedure' },
  { value: 'LAPAROSCOPIC', label: 'Laparoscopic Procedure' },
  { value: 'DIAGNOSTIC', label: 'Diagnostic Procedure' },
  { value: 'THERAPEUTIC', label: 'Therapeutic Procedure' },
  { value: 'OTHER', label: 'Other' },
];

export const ANESTHESIA_TYPE_OPTIONS: { value: AnesthesiaType; label: string }[] = [
  { value: 'GENERAL', label: 'General Anesthesia' },
  { value: 'REGIONAL', label: 'Regional Anesthesia' },
  { value: 'LOCAL', label: 'Local Anesthesia' },
  { value: 'SEDATION', label: 'Conscious Sedation' },
  { value: 'NONE', label: 'No Anesthesia' },
  { value: 'OTHER', label: 'Other' },
];

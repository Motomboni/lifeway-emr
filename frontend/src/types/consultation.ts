/**
 * Consultation Type Definitions
 */
export interface ConsultationData {
  history: string;
  examination: string;
  diagnosis: string;
  clinical_notes: string;
  merge_with_patient_record?: boolean;
}

export interface Consultation extends ConsultationData {
  id: number;
  visit_id: number;
  created_by: number;
  created_by_name?: string;
  created_at: string;
  updated_at: string;
  diagnosis_codes?: DiagnosisCode[];
}

/**
 * Diagnosis Code Type Definitions
 */
export interface DiagnosisCode {
  id: number;
  code_type: 'ICD11' | 'ICD10';
  code: string;
  description: string;
  is_primary: boolean;
  confidence?: number;
  created_by: number;
  created_by_name?: string;
  created_at: string;
  updated_at: string;
}

export interface DiagnosisCodeData {
  code_type?: 'ICD11' | 'ICD10';
  code: string;
  description: string;
  is_primary?: boolean;
  confidence?: number;
}

export interface ApplyAICodesRequest {
  icd11_codes: Array<{
    code: string;
    description: string;
    confidence?: number;
  }>;
  set_primary?: boolean;
}

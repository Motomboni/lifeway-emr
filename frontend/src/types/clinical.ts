/**
 * Clinical Type Definitions
 */

export interface VitalSigns {
  id: number;
  visit: number;
  recorded_by: number;
  recorded_by_name: string;
  temperature?: number | null;
  systolic_bp?: number | null;
  diastolic_bp?: number | null;
  pulse?: number | null;
  respiratory_rate?: number | null;
  oxygen_saturation?: number | null;
  weight?: number | null;
  height?: number | null;
  bmi?: number | null;
  muac?: number | null;
  nutritional_status?: string | null;
  urine_anc?: string | null;
  lmp?: string | null;
  edd?: string | null;
  ega_weeks?: number | null;
  ega_days?: number | null;
  notes?: string;
  recorded_at: string;
  abnormal_flags: string[];
}

export interface VitalSignsCreate {
  temperature?: number | null;
  systolic_bp?: number | null;
  diastolic_bp?: number | null;
  pulse?: number | null;
  respiratory_rate?: number | null;
  oxygen_saturation?: number | null;
  weight?: number | null;
  height?: number | null;
  muac?: number | null;
  nutritional_status?: string | null;
  urine_anc?: string | null;
  lmp?: string | null;
  edd?: string | null;
  ega_weeks?: number | null;
  ega_days?: number | null;
  notes?: string;
}

export interface ClinicalTemplate {
  id: number;
  name: string;
  category: string;
  description?: string;
  history_template?: string;
  examination_template?: string;
  diagnosis_template?: string;
  clinical_notes_template?: string;
  created_by: number;
  created_by_name: string;
  is_active: boolean;
  usage_count: number;
  created_at: string;
  updated_at: string;
}

export interface ClinicalTemplateCreate {
  name: string;
  category: string;
  description?: string;
  history_template?: string;
  examination_template?: string;
  diagnosis_template?: string;
  clinical_notes_template?: string;
  is_active?: boolean;
}

export interface ClinicalAlert {
  id: number;
  visit: number;
  alert_type: 'VITAL_SIGNS' | 'DRUG_INTERACTION' | 'ALLERGY' | 'LAB_CRITICAL' | 'CONTRAINDICATION' | 'DOSAGE';
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  title: string;
  message: string;
  related_resource_type?: string | null;
  related_resource_id?: number | null;
  acknowledged_by?: number | null;
  acknowledged_by_name?: string | null;
  acknowledged_at?: string | null;
  is_resolved: boolean;
  created_at: string;
}

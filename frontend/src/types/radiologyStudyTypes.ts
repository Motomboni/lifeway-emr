/**
 * Type definitions for Radiology Study Types Catalog.
 */

export type RadiologyStudyCategory = 
  | 'X_RAY'
  | 'CT_SCAN'
  | 'MRI'
  | 'ULTRASOUND'
  | 'MAMMOGRAPHY'
  | 'DEXA_SCAN'
  | 'NUCLEAR_MEDICINE'
  | 'FLUOROSCOPY'
  | 'ANGIOGRAPHY'
  | 'ECHOCARDIOGRAM'
  | 'OTHER';

export interface RadiologyStudyType {
  id: number;
  study_code: string;
  study_name: string;
  category: RadiologyStudyCategory;
  description: string;
  protocol: string;
  preparation_instructions: string;
  contrast_required: boolean;
  contrast_type: string;
  estimated_duration_minutes: number | null;
  body_part: string;
  is_active: boolean;
  requires_sedation: boolean;
  radiation_dose: string;
  created_by: number;
  created_by_name: string;
  created_at: string;
  updated_at: string;
}

export interface RadiologyStudyTypeCreate {
  study_code: string;
  study_name: string;
  category: RadiologyStudyCategory;
  description?: string;
  protocol?: string;
  preparation_instructions?: string;
  contrast_required?: boolean;
  contrast_type?: string;
  estimated_duration_minutes?: number | null;
  body_part?: string;
  is_active?: boolean;
  requires_sedation?: boolean;
  radiation_dose?: string;
}

export interface RadiologyStudyTypeUpdate {
  study_name?: string;
  category?: RadiologyStudyCategory;
  description?: string;
  protocol?: string;
  preparation_instructions?: string;
  contrast_required?: boolean;
  contrast_type?: string;
  estimated_duration_minutes?: number | null;
  body_part?: string;
  is_active?: boolean;
  requires_sedation?: boolean;
  radiation_dose?: string;
}

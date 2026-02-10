/**
 * Type definitions for Lab Test Catalog.
 */

export type LabTestCategory = 
  | 'HEMATOLOGY'
  | 'CHEMISTRY'
  | 'MICROBIOLOGY'
  | 'IMMUNOLOGY'
  | 'SEROLOGY'
  | 'ENDOCRINOLOGY'
  | 'TOXICOLOGY'
  | 'URINALYSIS'
  | 'BLOOD_BANK'
  | 'MOLECULAR'
  | 'OTHER';

export interface LabTestCatalog {
  id: number;
  test_code: string;
  test_name: string;
  category: LabTestCategory;
  description: string;
  reference_range_min: number | null;
  reference_range_max: number | null;
  reference_range_text: string;
  reference_range_display: string;
  unit: string;
  is_active: boolean;
  requires_fasting: boolean;
  turnaround_time_hours: number | null;
  specimen_type: string;
  created_by: number;
  created_by_name: string;
  created_at: string;
  updated_at: string;
}

export interface LabTestCatalogCreate {
  test_code: string;
  test_name: string;
  category: LabTestCategory;
  description?: string;
  reference_range_min?: number | null;
  reference_range_max?: number | null;
  reference_range_text?: string;
  unit?: string;
  is_active?: boolean;
  requires_fasting?: boolean;
  turnaround_time_hours?: number | null;
  specimen_type?: string;
}

export interface LabTestCatalogUpdate {
  test_name?: string;
  category?: LabTestCategory;
  description?: string;
  reference_range_min?: number | null;
  reference_range_max?: number | null;
  reference_range_text?: string;
  unit?: string;
  is_active?: boolean;
  requires_fasting?: boolean;
  turnaround_time_hours?: number | null;
  specimen_type?: string;
}

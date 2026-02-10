/**
 * Nursing Types
 * 
 * Types for Nurse-specific models:
 * - NursingNote
 * - MedicationAdministration
 * - LabSampleCollection
 */

export interface NursingNote {
  id: number;
  visit: number;
  visit_id?: number;
  recorded_by: number;
  recorded_by_name?: string;
  note_type: 'GENERAL' | 'ADMISSION' | 'SHIFT_HANDOVER' | 'PROCEDURE' | 'WOUND_CARE' | 'PATIENT_EDUCATION' | 'ANTENATAL' | 'INPATIENT' | 'OTHER';
  note_content: string;
  patient_condition?: string;
  care_provided?: string;
  patient_response?: string;
  recorded_at: string;
}

export interface NursingNoteCreate {
  note_type: NursingNote['note_type'];
  note_content: string;
  patient_condition?: string;
  care_provided?: string;
  patient_response?: string;
  merge_with_patient_record?: boolean;
}

export interface MedicationAdministration {
  id: number;
  visit: number;
  visit_id?: number;
  prescription: number;
  prescription_id?: number;
  prescription_details?: {
    drug?: string;
    drug_name?: string; // Backend may return either
    dosage?: string;
    frequency?: string;
  };
  administered_by: number;
  administered_by_name?: string;
  administration_time: string;
  dose_administered: string;
  route: 'ORAL' | 'IV' | 'IM' | 'SC' | 'TOPICAL' | 'INHALATION' | 'RECTAL' | 'OTHER';
  site?: string;
  status: 'GIVEN' | 'REFUSED' | 'HELD' | 'NOT_AVAILABLE' | 'ERROR';
  administration_notes?: string;
  reason_if_held?: string;
  recorded_at: string;
}

export interface MedicationAdministrationCreate {
  prescription: number;
  administration_time: string;
  dose_administered: string;
  route: MedicationAdministration['route'];
  site?: string;
  status: MedicationAdministration['status'];
  administration_notes?: string;
  reason_if_held?: string;
  merge_with_patient_record?: boolean;
}

export interface LabSampleCollection {
  id: number;
  visit: number;
  visit_id?: number;
  lab_order: number;
  lab_order_id?: number;
  lab_order_tests?: string[];
  collected_by: number;
  collected_by_name?: string;
  collection_time: string;
  sample_type: 'Blood' | 'Urine' | 'Stool' | 'Sputum' | 'Swab' | 'Tissue' | 'Other';
  collection_site?: string;
  status: 'COLLECTED' | 'PARTIAL' | 'FAILED' | 'REFUSED';
  sample_volume?: string;
  container_type?: string;
  collection_notes?: string;
  reason_if_failed?: string;
  recorded_at: string;
}

export interface LabSampleCollectionCreate {
  lab_order: number;
  collection_time: string;
  sample_type: LabSampleCollection['sample_type'];
  collection_site?: string;
  status: LabSampleCollection['status'];
  sample_volume?: string;
  container_type?: string;
  collection_notes?: string;
  reason_if_failed?: string;
  merge_with_patient_record?: boolean;
}

export interface PatientEducation {
  id: number;
  visit: number;
  visit_id?: number;
  topic: string;
  content: string;
  provided_by: number;
  provided_by_name?: string;
  provided_at: string;
  patient_understood?: boolean;
  notes?: string;
}

export interface PatientEducationCreate {
  topic: string;
  content: string;
  patient_understood?: boolean;
  notes?: string;
}

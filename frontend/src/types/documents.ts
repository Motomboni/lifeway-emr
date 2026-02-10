/**
 * Document Type Definitions
 */

export interface MedicalDocument {
  id: number;
  visit: number;
  document_type: 'LAB_REPORT' | 'RADIOLOGY_REPORT' | 'CONSULTATION_NOTE' | 'PRESCRIPTION' | 'REFERRAL_LETTER' | 'DISCHARGE_SUMMARY' | 'CONSENT_FORM' | 'INSURANCE_CARD' | 'ID_DOCUMENT' | 'OTHER';
  title: string;
  description?: string;
  file: string;
  file_url?: string;
  file_name?: string;
  file_size?: number | null;
  mime_type?: string;
  uploaded_by: number;
  uploaded_by_name: string;
  is_deleted: boolean;
  deleted_at?: string | null;
  deleted_by?: number | null;
  created_at: string;
  updated_at: string;
}

export interface MedicalDocumentCreate {
  document_type: MedicalDocument['document_type'];
  title: string;
  description?: string;
  file: File;
}

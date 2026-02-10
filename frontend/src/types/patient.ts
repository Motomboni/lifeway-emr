/**
 * TypeScript types for Patients
 */

export interface Patient {
  id: number;
  patient_id: string;
  first_name: string;
  last_name: string;
  middle_name?: string;
  full_name: string;
  date_of_birth?: string;
  age?: number;
  gender?: 'MALE' | 'FEMALE' | 'OTHER' | 'PREFER_NOT_TO_SAY';
  phone?: string;
  email?: string;
  address?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  emergency_contact_relationship?: string;
  national_id?: string;
  blood_group?: 'A+' | 'A-' | 'B+' | 'B-' | 'AB+' | 'AB-' | 'O+' | 'O-';
  allergies?: string;
  medical_history?: string;
  is_active: boolean;
  is_verified?: boolean;
  verified_by?: number;
  verified_at?: string;
  user?: number;
  user_username?: string;
  user_email?: string;
  has_retainership?: boolean;
  retainership_type?: string;
  retainership_start_date?: string;
  retainership_end_date?: string;
  retainership_amount?: number;
  has_active_insurance?: boolean;
  created_at: string;
  updated_at: string;
}

export interface PatientCreateData {
  first_name: string;
  last_name: string;
  middle_name?: string;
  date_of_birth?: string;
  gender?: 'MALE' | 'FEMALE' | 'OTHER' | 'PREFER_NOT_TO_SAY';
  phone?: string;
  email?: string;
  address?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  emergency_contact_relationship?: string;
  national_id?: string;
  blood_group?: 'A+' | 'A-' | 'B+' | 'B-' | 'AB+' | 'AB-' | 'O+' | 'O-';
  allergies?: string;
  medical_history?: string;
  // Insurance fields
  has_insurance?: boolean;
  insurance_provider_id?: number;
  insurance_policy_number?: string;
  insurance_coverage_type?: 'FULL' | 'PARTIAL';
  insurance_coverage_percentage?: number;
  insurance_valid_from?: string;
  insurance_valid_to?: string;
  // Retainership fields
  has_retainership?: boolean;
  retainership_type?: string;
  retainership_start_date?: string;
  retainership_end_date?: string;
  retainership_amount?: number;
}

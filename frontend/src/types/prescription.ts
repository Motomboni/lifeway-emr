/**
 * TypeScript types for Prescriptions
 */

export interface Prescription {
  id: number;
  visit_id: number;
  consultation: number;
  drug: string;
  drug_code?: string;
  dosage: string;
  frequency?: string;
  duration?: string;
  quantity?: string;
  instructions?: string;
  status: 'PENDING' | 'DISPENSED' | 'CANCELLED';
  dispensed: boolean;
  dispensed_date?: string;
  dispensing_notes?: string;
  prescribed_by: number;
  dispensed_by?: number;
  created_at: string;
  updated_at: string;
}

export interface PrescriptionCreateData {
  drug: string;
  drug_code?: string;
  dosage: string;
  frequency?: string;
  duration?: string;
  quantity?: string;
  instructions?: string;
}

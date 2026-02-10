/**
 * TypeScript types for Visits
 */

export interface PatientRetainership {
  has_retainership: boolean;
  is_active: boolean;
  retainership_type?: string;
  retainership_start_date?: string;
  retainership_end_date?: string;
  retainership_amount?: string;
  discount_percentage: string;
  days_until_expiry?: number;
  is_expired: boolean;
}

export interface Visit {
  id: number;
  patient: number;
  patient_name?: string;
  patient_id?: string;
  visit_type?: 'CONSULTATION' | 'FOLLOW_UP' | 'EMERGENCY' | 'ROUTINE' | 'SPECIALIST';
  chief_complaint?: string;
  appointment?: number;
  status: 'OPEN' | 'CLOSED';
  payment_status: 'UNPAID' | 'PARTIALLY_PAID' | 'PAID' | 'INSURANCE_PENDING' | 'INSURANCE_CLAIMED' | 'SETTLED' | 'PENDING' | 'CLEARED';
  payment_type?: 'CASH' | 'INSURANCE';
  patient_retainership?: PatientRetainership;
  closed_by?: number;
  closed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface VisitCreateData {
  patient: number;
  visit_type?: 'CONSULTATION' | 'FOLLOW_UP' | 'EMERGENCY' | 'ROUTINE' | 'SPECIALIST';
  chief_complaint?: string;
  appointment?: number;
  payment_status?: 'UNPAID' | 'PARTIALLY_PAID' | 'PAID' | 'INSURANCE_PENDING' | 'INSURANCE_CLAIMED' | 'SETTLED';
  payment_type?: 'CASH' | 'INSURANCE';
}

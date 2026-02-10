/**
 * Type definitions for Referrals.
 */

export type ReferralStatus = 
  | 'PENDING'
  | 'ACCEPTED'
  | 'REJECTED'
  | 'COMPLETED'
  | 'CANCELLED';

export type ReferralSpecialty = 
  | 'CARDIOLOGY'
  | 'DERMATOLOGY'
  | 'ENDOCRINOLOGY'
  | 'GASTROENTEROLOGY'
  | 'HEMATOLOGY'
  | 'INFECTIOUS_DISEASE'
  | 'NEPHROLOGY'
  | 'NEUROLOGY'
  | 'ONCOLOGY'
  | 'OPHTHALMOLOGY'
  | 'ORTHOPEDICS'
  | 'OTOLARYNGOLOGY'
  | 'PEDIATRICS'
  | 'PSYCHIATRY'
  | 'PULMONOLOGY'
  | 'RHEUMATOLOGY'
  | 'UROLOGY'
  | 'OTHER';

export type ReferralUrgency = 
  | 'ROUTINE'
  | 'URGENT'
  | 'EMERGENCY';

export interface Referral {
  id: number;
  visit_id: number;
  consultation_id: number;
  specialty: ReferralSpecialty;
  specialist_name: string;
  specialist_contact: string;
  reason: string;
  clinical_summary: string;
  urgency: ReferralUrgency;
  status: ReferralStatus;
  referred_by: number;
  referred_by_name: string;
  accepted_at: string | null;
  completed_at: string | null;
  specialist_notes: string;
  created_at: string;
  updated_at: string;
}

export interface ReferralCreate {
  consultation: number;
  specialty: ReferralSpecialty;
  specialist_name: string;
  specialist_contact?: string;
  reason: string;
  clinical_summary?: string;
  urgency: ReferralUrgency;
}

export interface ReferralUpdate {
  status?: ReferralStatus;
  specialist_notes?: string;
}

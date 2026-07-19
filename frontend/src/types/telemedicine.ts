/**
 * Telemedicine TypeScript types
 */

export type TelemedicineClinicRole =
  | 'HOST'
  | 'PATIENT'
  | 'NURSE'
  | 'SPECIALIST'
  | 'OBSERVER'
  | 'STAFF';

export type TelemedicineInviteStatus =
  | 'PENDING'
  | 'ACCEPTED'
  | 'DECLINED'
  | 'REVOKED';

export interface TelemedicineSession {
  id: number;
  visit: number;
  appointment?: number | null;
  twilio_room_sid: string;
  twilio_room_name: string;
  video_provider?: 'twilio' | 'livekit' | '';
  status: 'SCHEDULED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED' | 'FAILED';
  doctor: number;
  doctor_name: string;
  doctor_display_name?: string;
  patient: number;
  patient_name: string;
  scheduled_start: string;
  actual_start?: string | null;
  actual_end?: string | null;
  duration_seconds?: number | null;
  duration_minutes?: number | null;
  recording_enabled: boolean;
  recording_sid?: string | null;
  recording_url?: string | null;
  notes?: string | null;
  transcription_status?: string | null;
  transcription_text?: string | null;
  transcription_requested_at?: string | null;
  transcription_completed_at?: string | null;
  error_message?: string | null;
  created_by: number;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  participants: TelemedicineParticipant[];
  meeting_link?: string | null;
  my_invite_status?: TelemedicineInviteStatus | null;
  my_clinic_role?: TelemedicineClinicRole | null;
}

/** Response from end session when add_billing was requested */
export interface TelemedicineEndSessionResponse extends TelemedicineSession {
  billing_added?: boolean;
}

export interface TelemedicineParticipant {
  id: number;
  user: number;
  user_name: string;
  user_role: string;
  clinic_role?: TelemedicineClinicRole;
  invite_status?: TelemedicineInviteStatus;
  invited_by?: number | null;
  invited_by_name?: string | null;
  invited_at?: string | null;
  invite_message?: string;
  twilio_participant_sid?: string | null;
  joined_at?: string | null;
  left_at?: string | null;
  connection_quality?: string | null;
  device_type?: string | null;
  browser?: string | null;
}

export interface TelemedicineSessionCreate {
  visit: number;
  appointment?: number | null;
  scheduled_start: string;
  recording_enabled?: boolean;
  recording_consent_acknowledged?: boolean;
  notes?: string | null;
}

export interface TelemedicineAccessToken {
  token: string;
  room_name: string;
  room_sid?: string;
  session_id: number;
  video_provider?: 'twilio' | 'livekit';
  livekit_url?: string;
}

export interface TelemedicineInvitableStaff {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  is_active: boolean;
}

export interface TelemedicineInviteRequest {
  user_id: number;
  clinic_role?: 'NURSE' | 'SPECIALIST' | 'OBSERVER' | 'STAFF';
  message?: string;
}

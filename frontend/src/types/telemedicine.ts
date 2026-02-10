/**
 * Telemedicine TypeScript types
 */

export interface TelemedicineSession {
  id: number;
  visit: number;
  appointment?: number | null;
  twilio_room_sid: string;
  twilio_room_name: string;
  status: 'SCHEDULED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED' | 'FAILED';
  doctor: number;
  doctor_name: string;
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
  notes?: string | null;
}

export interface TelemedicineAccessToken {
  token: string;
  room_name: string;
  room_sid?: string;
  session_id: number;
}

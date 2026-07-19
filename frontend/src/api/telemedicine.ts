/**
 * Telemedicine API Client
 *
 * Endpoints:
 * - GET /api/v1/telemedicine/ - List sessions
 * - POST /api/v1/telemedicine/ - Create session
 * - GET /api/v1/telemedicine/{id}/ - Get session
 * - POST /api/v1/telemedicine/{id}/start/ - Start session
 * - POST /api/v1/telemedicine/{id}/end/ - End session
 * - GET /api/v1/telemedicine/{id}/recording/ - Stream recording (proxy, requires auth)
 * - POST /api/v1/telemedicine/token/ - Get access token
 * - POST /api/v1/telemedicine/{id}/leave/ - Leave session
 * - Virtual clinic staff invites
 */
import { apiRequest } from '../utils/apiClient';
import {
  TelemedicineSession,
  TelemedicineSessionCreate,
  TelemedicineAccessToken,
  TelemedicineInvitableStaff,
  TelemedicineInviteRequest,
  TelemedicineParticipant,
} from '../types/telemedicine';

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

/**
 * Fetch telemedicine sessions
 */
export async function fetchTelemedicineSessions(
  visitId?: number
): Promise<TelemedicineSession[]> {
  const params = new URLSearchParams();
  if (visitId) {
    params.append('visit_id', visitId.toString());
  }
  
  const queryString = params.toString();
  const url = `/telemedicine/${queryString ? `?${queryString}` : ''}`;
  return apiRequest<TelemedicineSession[]>(url);
}

/**
 * Get a telemedicine session by ID
 */
export async function getTelemedicineSession(
  sessionId: number
): Promise<TelemedicineSession> {
  return apiRequest<TelemedicineSession>(`/telemedicine/${sessionId}/`);
}

/**
 * Create a telemedicine session
 */
export async function createTelemedicineSession(
  data: TelemedicineSessionCreate
): Promise<TelemedicineSession> {
  return apiRequest<TelemedicineSession>('/telemedicine/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Start a telemedicine session
 */
export async function startTelemedicineSession(
  sessionId: number
): Promise<TelemedicineSession> {
  return apiRequest<TelemedicineSession>(`/telemedicine/${sessionId}/start/`, {
    method: 'POST',
  });
}

/**
 * End a telemedicine session.
 * Optionally add a billing line item for the session (add_billing: true).
 */
export async function endTelemedicineSession(
  sessionId: number,
  options?: { add_billing?: boolean }
): Promise<TelemedicineSession & { billing_added?: boolean }> {
  return apiRequest<TelemedicineSession & { billing_added?: boolean }>(
    `/telemedicine/${sessionId}/end/`,
    {
      method: 'POST',
      body: JSON.stringify(options?.add_billing ? { add_billing: true } : {}),
    }
  );
}

/**
 * Request automatic transcription of the session recording (completed sessions only).
 */
export async function requestTelemedicineTranscription(
  sessionId: number
): Promise<TelemedicineSession> {
  return apiRequest<TelemedicineSession>(
    `/telemedicine/${sessionId}/request-transcription/`,
    { method: 'POST' }
  );
}

/** Save live browser speech-to-text captured during a video call */
export async function saveLiveTelemedicineTranscript(
  sessionId: number,
  transcript: string,
): Promise<TelemedicineSession> {
  return apiRequest<TelemedicineSession>(
    `/telemedicine/${sessionId}/save-live-transcript/`,
    {
      method: 'POST',
      body: JSON.stringify({ transcript }),
    },
  );
}

/**
 * Get Twilio access token for joining a session
 */
export async function getTelemedicineAccessToken(
  sessionId: number
): Promise<TelemedicineAccessToken> {
  return apiRequest<TelemedicineAccessToken>('/telemedicine/token/', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId }),
  });
}

/**
 * Leave a telemedicine session
 */
export async function leaveTelemedicineSession(
  sessionId: number
): Promise<void> {
  return apiRequest<void>(`/telemedicine/${sessionId}/leave/`, {
    method: 'POST',
  });
}

/**
 * URL for the session recording (proxied by backend with Twilio auth).
 * Use with fetch + Authorization header to stream the recording.
 */
export function getTelemedicineRecordingUrl(sessionId: number): string {
  return `${API_BASE}/telemedicine/${sessionId}/recording/`;
}

/**
 * Create a telemedicine session from an appointment (doctor).
 * POST /api/v1/telemedicine/create-session/
 */
export async function createSessionFromAppointment(
  appointmentId: number,
  options?: { recording_enabled?: boolean }
): Promise<TelemedicineSession & { meeting_link?: string }> {
  return apiRequest<TelemedicineSession & { meeting_link?: string }>(
    '/telemedicine/create-session/',
    {
      method: 'POST',
      body: JSON.stringify({
        appointment_id: appointmentId,
        recording_enabled: options?.recording_enabled ?? true,
      }),
    }
  );
}

/**
 * Get meeting link (and access token if Twilio) for joining a session.
 * GET /api/v1/telemedicine/{id}/join/
 */
export async function getTelemedicineJoinLink(
  sessionId: number
): Promise<{ meeting_link: string; session_id: number; access_token?: string; room_name?: string }> {
  return apiRequest<{ meeting_link: string; session_id: number; access_token?: string; room_name?: string }>(
    `/telemedicine/${sessionId}/join/`
  );
}

/** List staff who can be invited into a virtual clinic room */
export async function fetchInvitableStaff(
  sessionId: number,
  role?: string,
): Promise<TelemedicineInvitableStaff[]> {
  const params = role ? `?role=${encodeURIComponent(role)}` : '';
  return apiRequest<TelemedicineInvitableStaff[]>(
    `/telemedicine/${sessionId}/invitable-staff/${params}`,
  );
}

/** Invite clinical staff into the virtual clinic */
export async function inviteTelemedicineStaff(
  sessionId: number,
  data: TelemedicineInviteRequest,
): Promise<TelemedicineParticipant> {
  return apiRequest<TelemedicineParticipant>(`/telemedicine/${sessionId}/invite/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/** Revoke a staff invite */
export async function revokeTelemedicineInvite(
  sessionId: number,
  participantId: number,
): Promise<TelemedicineParticipant> {
  return apiRequest<TelemedicineParticipant>(
    `/telemedicine/${sessionId}/invites/${participantId}/revoke/`,
    { method: 'POST' },
  );
}

/** Accept or decline a virtual clinic invite */
export async function respondTelemedicineInvite(
  sessionId: number,
  accept: boolean,
): Promise<TelemedicineParticipant> {
  return apiRequest<TelemedicineParticipant>(
    `/telemedicine/${sessionId}/respond-invite/`,
    {
      method: 'POST',
      body: JSON.stringify({ accept }),
    },
  );
}

export interface TelemedicinePricing {
  configured: boolean;
  can_edit?: boolean;
  created?: boolean;
  service_id?: number;
  service_code?: string;
  name?: string;
  amount?: string;
  currency?: string;
  is_active?: boolean;
  description?: string;
  updated_at?: string | null;
  detail?: string;
}

/** Get telemedicine consultation price */
export async function fetchTelemedicinePricing(): Promise<TelemedicinePricing> {
  return apiRequest<TelemedicinePricing>('/telemedicine/pricing/');
}

/** Admin: set telemedicine consultation price */
export async function updateTelemedicinePricing(data: {
  amount: string | number;
  name?: string;
  is_active?: boolean;
  description?: string;
}): Promise<TelemedicinePricing> {
  return apiRequest<TelemedicinePricing>('/telemedicine/pricing/', {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

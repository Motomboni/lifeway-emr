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
 */
import { apiRequest } from '../utils/apiClient';
import {
  TelemedicineSession,
  TelemedicineSessionCreate,
  TelemedicineAccessToken,
} from '../types/telemedicine';

const API_BASE = process.env.REACT_APP_API_URL || '/api/v1';

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
        recording_enabled: options?.recording_enabled ?? false,
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

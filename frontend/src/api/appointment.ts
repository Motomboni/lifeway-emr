/**
 * Appointment API Client
 * 
 * Endpoints:
 * - GET    /api/v1/appointments/          - List appointments
 * - POST   /api/v1/appointments/          - Create appointment (Receptionist)
 * - GET    /api/v1/appointments/{id}/     - Get appointment
 * - PUT    /api/v1/appointments/{id}/     - Update appointment
 * - PATCH  /api/v1/appointments/{id}/     - Partial update appointment
 * - DELETE /api/v1/appointments/{id}/     - Cancel appointment
 * - POST   /api/v1/appointments/{id}/confirm/ - Confirm appointment
 * - POST   /api/v1/appointments/{id}/complete/ - Complete appointment
 * - POST   /api/v1/appointments/{id}/cancel/ - Cancel appointment
 * - GET    /api/v1/appointments/upcoming/ - Get upcoming appointments
 * - GET    /api/v1/appointments/today/    - Get today's appointments
 */
import { apiRequest } from '../utils/apiClient';
import {
  Appointment,
  AppointmentCreateData,
  AppointmentUpdateData,
  AppointmentFilters,
} from '../types/appointment';

// Re-export types for convenience
export type {
  Appointment,
  AppointmentCreateData,
  AppointmentUpdateData,
  AppointmentFilters,
} from '../types/appointment';

export interface PaginatedAppointmentResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Appointment[];
}

/**
 * Fetch appointments (with optional filters and pagination)
 */
export async function fetchAppointments(
  filters?: AppointmentFilters
): Promise<Appointment[] | PaginatedAppointmentResponse> {
  const params = new URLSearchParams();
  if (filters?.patient) params.append('patient', filters.patient.toString());
  if (filters?.doctor) params.append('doctor', filters.doctor.toString());
  if (filters?.status) params.append('status', filters.status);
  if (filters?.date_from) params.append('date_from', filters.date_from);
  if (filters?.date_to) params.append('date_to', filters.date_to);
  if (filters?.search) params.append('search', filters.search);
  if (filters?.page) params.append('page', filters.page.toString());
  if (filters?.page_size) params.append('page_size', filters.page_size.toString());
  
  const queryString = params.toString();
  const endpoint = queryString ? `/appointments/?${queryString}` : '/appointments/';
  return apiRequest<Appointment[] | PaginatedAppointmentResponse>(endpoint);
}

/**
 * Get appointment by ID
 */
export async function getAppointment(appointmentId: number): Promise<Appointment> {
  return apiRequest<Appointment>(`/appointments/${appointmentId}/`);
}

/**
 * Create a new appointment (Receptionist only)
 */
export async function createAppointment(
  appointmentData: AppointmentCreateData
): Promise<Appointment> {
  return apiRequest<Appointment>('/appointments/', {
    method: 'POST',
    body: JSON.stringify(appointmentData),
  });
}

/**
 * Update an appointment
 */
export async function updateAppointment(
  appointmentId: number,
  appointmentData: AppointmentUpdateData
): Promise<Appointment> {
  return apiRequest<Appointment>(`/appointments/${appointmentId}/`, {
    method: 'PUT',
    body: JSON.stringify(appointmentData),
  });
}

/**
 * Partially update an appointment
 */
export async function partialUpdateAppointment(
  appointmentId: number,
  appointmentData: Partial<AppointmentUpdateData>
): Promise<Appointment> {
  return apiRequest<Appointment>(`/appointments/${appointmentId}/`, {
    method: 'PATCH',
    body: JSON.stringify(appointmentData),
  });
}

/**
 * Cancel an appointment
 */
export async function cancelAppointment(
  appointmentId: number,
  cancellationReason?: string
): Promise<Appointment> {
  return apiRequest<Appointment>(`/appointments/${appointmentId}/cancel/`, {
    method: 'POST',
    body: JSON.stringify({
      cancellation_reason: cancellationReason || '',
    }),
  });
}

/**
 * Confirm an appointment
 */
export async function confirmAppointment(appointmentId: number): Promise<Appointment> {
  return apiRequest<Appointment>(`/appointments/${appointmentId}/confirm/`, {
    method: 'POST',
  });
}

/**
 * Complete an appointment
 */
export async function completeAppointment(appointmentId: number): Promise<Appointment> {
  return apiRequest<Appointment>(`/appointments/${appointmentId}/complete/`, {
    method: 'POST',
  });
}

/**
 * Get upcoming appointments
 */
export async function fetchUpcomingAppointments(): Promise<
  Appointment[] | PaginatedAppointmentResponse
> {
  return apiRequest<Appointment[] | PaginatedAppointmentResponse>('/appointments/upcoming/');
}

/**
 * Get today's appointments
 */
export async function fetchTodayAppointments(): Promise<
  Appointment[] | PaginatedAppointmentResponse
> {
  return apiRequest<Appointment[] | PaginatedAppointmentResponse>('/appointments/today/');
}

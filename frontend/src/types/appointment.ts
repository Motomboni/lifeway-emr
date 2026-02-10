/**
 * TypeScript types for Appointments
 */

export interface Appointment {
  id: number;
  patient: number;
  patient_name?: string;
  patient_id?: string;
  doctor: number;
  doctor_name?: string;
  visit?: number | null;
  appointment_date: string;
  duration_minutes: number;
  status: 'SCHEDULED' | 'CONFIRMED' | 'COMPLETED' | 'CANCELLED' | 'NO_SHOW';
  reason?: string;
  notes?: string;
  created_by: number;
  created_by_name?: string;
  created_at: string;
  updated_at: string;
  cancelled_at?: string | null;
  cancelled_by?: number | null;
  cancelled_by_name?: string | null;
  cancellation_reason?: string;
}

export interface AppointmentCreateData {
  patient: number;
  doctor: number;
  appointment_date: string; // ISO 8601 format
  duration_minutes?: number;
  reason?: string;
  notes?: string;
}

export interface AppointmentUpdateData {
  appointment_date?: string;
  duration_minutes?: number;
  status?: 'SCHEDULED' | 'CONFIRMED' | 'COMPLETED' | 'CANCELLED' | 'NO_SHOW';
  reason?: string;
  notes?: string;
  visit?: number | null;
  cancellation_reason?: string;
}

export interface AppointmentFilters {
  patient?: number;
  doctor?: number;
  status?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

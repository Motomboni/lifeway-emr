/**
 * API client for Patient Portal (read-only access for patients).
 */
import { apiRequest } from '../utils/apiClient';
import type { Patient } from '../types/patient';
import type { Visit } from '../types/visit';
import type { Appointment } from '../types/appointment';
import type { LabResult } from '../types/lab';
import type { Prescription } from '../types/prescription';
import type { RadiologyResult, PatientPortalMedicalHistory } from '../types/patientPortal';

/**
 * Get patient's own profile
 */
export async function getPatientProfile(): Promise<Patient> {
  return apiRequest<Patient>('/patient-portal/profile/');
}

/**
 * Get patient's own visits
 */
export async function getPatientVisits(): Promise<Visit[]> {
  const data = await apiRequest<Visit[]>('/patient-portal/visits/');
  return Array.isArray(data) ? data : [];
}

/**
 * Get details of a specific visit (patient's own only)
 */
export async function getPatientVisitDetail(visitId: number): Promise<Visit> {
  return apiRequest<Visit>(`/patient-portal/visits/${visitId}/`);
}

/**
 * Get patient's own appointments
 */
export async function getPatientAppointments(): Promise<Appointment[]> {
  const data = await apiRequest<Appointment[]>('/patient-portal/appointments/');
  return Array.isArray(data) ? data : [];
}

/**
 * Get patient's own lab results
 */
export async function getPatientLabResults(): Promise<LabResult[]> {
  const data = await apiRequest<LabResult[]>('/patient-portal/lab-results/');
  return Array.isArray(data) ? data : [];
}

/**
 * Get patient's own radiology results
 */
export async function getPatientRadiologyResults(): Promise<RadiologyResult[]> {
  const data = await apiRequest<RadiologyResult[]>('/patient-portal/radiology-results/');
  return Array.isArray(data) ? data : [];
}

/**
 * Get patient's own prescriptions
 */
export async function getPatientPrescriptions(): Promise<Prescription[]> {
  const data = await apiRequest<Prescription[]>('/patient-portal/prescriptions/');
  return Array.isArray(data) ? data : [];
}

/**
 * Get patient's comprehensive medical history
 */
export async function getPatientMedicalHistory(): Promise<PatientPortalMedicalHistory> {
  return apiRequest<PatientPortalMedicalHistory>('/patient-portal/medical-history/');
}

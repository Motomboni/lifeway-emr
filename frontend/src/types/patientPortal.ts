/**
 * Type definitions for Patient Portal.
 */
import type { Patient } from './patient';
import type { Visit } from './visit';
import type { Consultation } from './consultation';
import type { Appointment } from './appointment';
import type { LabResult } from './lab';
import type { Prescription } from './prescription';

// Re-export types for use in patient portal
export type { Patient, Visit, Consultation, Appointment, LabResult, Prescription };

// Re-export RadiologyResult type if it exists, otherwise define a basic one
export interface RadiologyResult {
  id: number;
  radiology_request_id: number;
  report: string;
  finding_flag: 'NORMAL' | 'ABNORMAL' | 'CRITICAL';
  image_count: number;
  image_metadata: Record<string, any>;
  reported_by: number;
  reported_at: string;
}

export interface PatientPortalProfile {
  patient: Patient;
}

export interface PatientPortalVisits {
  visits: Visit[];
}

export interface PatientPortalVisitDetail {
  visit: Visit;
  consultation?: Consultation;
  lab_results?: LabResult[];
  radiology_results?: RadiologyResult[];
  prescriptions?: Prescription[];
}

export interface PatientPortalAppointments {
  appointments: Appointment[];
}

export interface PatientPortalLabResults {
  lab_results: LabResult[];
}

export interface PatientPortalRadiologyResults {
  radiology_results: RadiologyResult[];
}

export interface PatientPortalPrescriptions {
  prescriptions: Prescription[];
}

export interface PatientPortalMedicalHistory {
  patient: Patient;
  visits: Visit[];
  consultations: Consultation[];
  lab_results: LabResult[];
  radiology_results: RadiologyResult[];
  prescriptions: Prescription[];
  appointments: Appointment[];
}

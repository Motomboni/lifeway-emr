/**
 * API client functions for Admission, Ward, and Bed management.
 */
import { apiRequest } from '../utils/apiClient';

// Types
export interface Ward {
  id: number;
  name: string;
  code: string;
  description?: string;
  capacity: number;
  is_active: boolean;
  available_beds_count: number;
  occupied_beds_count: number;
  created_at: string;
  updated_at: string;
}

export interface Bed {
  id: number;
  ward: number;
  ward_name?: string;
  ward_code?: string;
  bed_number: string;
  bed_type: 'STANDARD' | 'PRIVATE' | 'SEMI_PRIVATE' | 'ICU' | 'ISOLATION' | 'MATERNITY';
  is_available: boolean;
  is_active: boolean;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface Admission {
  id: number;
  visit: number;
  visit_id: number;
  ward: number;
  ward_name: string;
  ward_code: string;
  bed: number;
  bed_number: string;
  admission_type: 'EMERGENCY' | 'ELECTIVE' | 'OBSERVATION' | 'DAY_CARE';
  admission_source: 'OUTPATIENT' | 'EMERGENCY' | 'REFERRAL' | 'TRANSFER' | 'DIRECT';
  admission_date: string;
  admission_status: 'ADMITTED' | 'DISCHARGED' | 'TRANSFERRED' | 'ABSENT';
  discharge_date?: string;
  discharge_summary?: number;
  admitting_doctor: number;
  admitting_doctor_name: string;
  chief_complaint: string;
  admission_notes?: string;
  transferred_from?: number;
  patient_name: string;
  patient_id: string;
  length_of_stay_days: number;
  created_at: string;
  updated_at: string;
}

export interface AdmissionCreateData {
  visit: number;
  ward: number;
  bed: number;
  admission_type: 'EMERGENCY' | 'ELECTIVE' | 'OBSERVATION' | 'DAY_CARE';
  admission_source: 'OUTPATIENT' | 'EMERGENCY' | 'REFERRAL' | 'TRANSFER' | 'DIRECT';
  admission_date?: string;
  chief_complaint: string;
  admission_notes?: string;
  // Enhanced clinical fields
  history_of_present_illness?: string;
  past_medical_history?: string;
  allergies?: string;
  current_medications?: string;
  vital_signs_at_admission?: string;
  physical_examination?: string;
  provisional_diagnosis?: string;
  plan_of_care?: string;
}

export interface AdmissionUpdateData {
  admission_status?: 'ADMITTED' | 'DISCHARGED' | 'TRANSFERRED' | 'ABSENT';
  admission_notes?: string;
  discharge_date?: string;
}

export interface AdmissionTransferData {
  new_ward_id: number;
  new_bed_id: number;
  transfer_notes?: string;
}

// Ward endpoints
export const fetchWards = async (isActive?: boolean): Promise<Ward[]> => {
  const params = new URLSearchParams();
  if (isActive !== undefined) {
    params.append('is_active', isActive.toString());
  }
  const queryString = params.toString();
  const endpoint = queryString ? `/admissions/wards/?${queryString}` : '/admissions/wards/';
  return apiRequest<Ward[]>(endpoint);
};

export const fetchWard = async (wardId: number): Promise<Ward> => {
  return apiRequest<Ward>(`/admissions/wards/${wardId}/`);
};

export const createWard = async (data: Partial<Ward>): Promise<Ward> => {
  return apiRequest<Ward>('/admissions/wards/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

export const updateWard = async (wardId: number, data: Partial<Ward>): Promise<Ward> => {
  return apiRequest<Ward>(`/admissions/wards/${wardId}/`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
};

export const fetchWardBeds = async (wardId: number): Promise<Bed[]> => {
  return apiRequest<Bed[]>(`/admissions/wards/${wardId}/beds/`);
};

export const fetchWardAvailableBeds = async (wardId: number): Promise<Bed[]> => {
  return apiRequest<Bed[]>(`/admissions/wards/${wardId}/available_beds/`);
};

// Bed endpoints
export const fetchBeds = async (params?: {
  ward?: number;
  is_available?: boolean;
  is_active?: boolean;
}): Promise<Bed[]> => {
  const searchParams = new URLSearchParams();
  if (params?.ward) searchParams.append('ward', params.ward.toString());
  if (params?.is_available !== undefined) searchParams.append('is_available', params.is_available.toString());
  if (params?.is_active !== undefined) searchParams.append('is_active', params.is_active.toString());
  const queryString = searchParams.toString();
  const endpoint = queryString ? `/admissions/beds/?${queryString}` : '/admissions/beds/';
  return apiRequest<Bed[]>(endpoint);
};

export const fetchBed = async (bedId: number): Promise<Bed> => {
  return apiRequest<Bed>(`/admissions/beds/${bedId}/`);
};

export const createBed = async (data: Partial<Bed>): Promise<Bed> => {
  return apiRequest<Bed>('/admissions/beds/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

export const updateBed = async (bedId: number, data: Partial<Bed>): Promise<Bed> => {
  return apiRequest<Bed>(`/admissions/beds/${bedId}/`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
};

// Admission endpoints (visit-scoped)
export const fetchAdmission = async (visitId: number): Promise<Admission | null> => {
  try {
    const response = await apiRequest<any>(`/visits/${visitId}/admissions/`);
    // Handle both array and paginated responses
    const admissions = Array.isArray(response) 
      ? response 
      : (response.results || []);
    return admissions.length > 0 ? admissions[0] : null;
  } catch (error: any) {
    if (error.status === 404) {
      return null;
    }
    throw error;
  }
};

export const createAdmission = async (visitId: number, data: AdmissionCreateData): Promise<Admission> => {
  return apiRequest<Admission>(`/visits/${visitId}/admissions/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

export const updateAdmission = async (visitId: number, admissionId: number, data: AdmissionUpdateData): Promise<Admission> => {
  return apiRequest<Admission>(`/visits/${visitId}/admissions/${admissionId}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
};

export const dischargeAdmission = async (visitId: number, admissionId: number, dischargeDate?: string): Promise<Admission> => {
  return apiRequest<Admission>(`/visits/${visitId}/admissions/${admissionId}/discharge/`, {
    method: 'POST',
    body: JSON.stringify({ discharge_date: dischargeDate }),
  });
};

export const transferAdmission = async (visitId: number, admissionId: number, data: AdmissionTransferData): Promise<Admission> => {
  return apiRequest<Admission>(`/visits/${visitId}/admissions/${admissionId}/transfer/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

// Inpatient list (all current inpatients)
export const fetchInpatients = async (wardId?: number): Promise<Admission[]> => {
  const params = new URLSearchParams();
  if (wardId) {
    params.append('ward', wardId.toString());
  }
  const queryString = params.toString();
  const endpoint = queryString ? `/admissions/inpatients/?${queryString}` : '/admissions/inpatients/';
  return apiRequest<Admission[]>(endpoint);
};


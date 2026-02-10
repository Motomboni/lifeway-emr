/**
 * Clinical API Client
 * 
 * Endpoints:
 * - GET /api/v1/visits/{visit_id}/clinical/vital-signs/ - List vital signs
 * - POST /api/v1/visits/{visit_id}/clinical/vital-signs/ - Create vital signs
 * - GET /api/v1/visits/{visit_id}/clinical/alerts/ - List alerts
 * - POST /api/v1/visits/{visit_id}/clinical/alerts/{id}/acknowledge/ - Acknowledge alert
 * - GET /api/v1/clinical/templates/ - List templates
 * - POST /api/v1/clinical/templates/ - Create template
 * - POST /api/v1/clinical/templates/{id}/use/ - Use template
 */
import { apiRequest } from '../utils/apiClient';
import {
  VitalSigns,
  VitalSignsCreate,
  ClinicalTemplate,
  ClinicalTemplateCreate,
  ClinicalAlert,
} from '../types/clinical';

/**
 * Fetch vital signs for a visit
 */
export async function fetchVitalSigns(visitId: number): Promise<VitalSigns[]> {
  return apiRequest<VitalSigns[]>(`/visits/${visitId}/clinical/vital-signs/`);
}

/**
 * Create vital signs record
 */
export async function createVitalSigns(
  visitId: number,
  data: VitalSignsCreate
): Promise<VitalSigns> {
  return apiRequest<VitalSigns>(`/visits/${visitId}/clinical/vital-signs/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Fetch clinical alerts for a visit
 */
export async function fetchClinicalAlerts(
  visitId: number,
  isResolved?: boolean
): Promise<ClinicalAlert[]> {
  const params = new URLSearchParams();
  if (isResolved !== undefined) {
    params.append('is_resolved', isResolved.toString());
  }
  const queryString = params.toString();
  return apiRequest<ClinicalAlert[]>(
    `/visits/${visitId}/clinical/alerts/${queryString ? `?${queryString}` : ''}`
  );
}

/**
 * Acknowledge a clinical alert
 */
export async function acknowledgeAlert(
  visitId: number,
  alertId: number
): Promise<ClinicalAlert> {
  return apiRequest<ClinicalAlert>(
    `/visits/${visitId}/clinical/alerts/${alertId}/acknowledge/`,
    {
      method: 'POST',
    }
  );
}

/**
 * Resolve a clinical alert
 */
export async function resolveAlert(
  visitId: number,
  alertId: number
): Promise<ClinicalAlert> {
  return apiRequest<ClinicalAlert>(
    `/visits/${visitId}/clinical/alerts/${alertId}/resolve/`,
    {
      method: 'POST',
    }
  );
}

/**
 * Fetch clinical templates
 */
export async function fetchClinicalTemplates(
  category?: string
): Promise<ClinicalTemplate[]> {
  const params = new URLSearchParams();
  if (category) {
    params.append('category', category);
  }
  const queryString = params.toString();
  return apiRequest<ClinicalTemplate[]>(
    `/clinical/templates/${queryString ? `?${queryString}` : ''}`
  );
}

/**
 * Create clinical template
 */
export async function createClinicalTemplate(
  data: ClinicalTemplateCreate
): Promise<ClinicalTemplate> {
  return apiRequest<ClinicalTemplate>('/clinical/templates/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Apply a clinical template (returns template content)
 */
export async function applyClinicalTemplate(
  templateId: number
): Promise<{
  history: string;
  examination: string;
  diagnosis: string;
  clinical_notes: string;
}> {
  return apiRequest<{
    history: string;
    examination: string;
    diagnosis: string;
    clinical_notes: string;
  }>(`/clinical/templates/${templateId}/use/`, {
    method: 'POST',
  });
}

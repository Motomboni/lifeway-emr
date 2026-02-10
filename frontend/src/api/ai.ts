/**
 * AI Integration API Client
 * 
 * All endpoints are visit-scoped:
 * - POST /api/v1/visits/{visitId}/ai/clinical-decision-support/
 * - POST /api/v1/visits/{visitId}/ai/nlp-summarize/
 * - POST /api/v1/visits/{visitId}/ai/automated-coding/
 * - POST /api/v1/visits/{visitId}/ai/drug-interaction-check/
 * - GET  /api/v1/visits/{visitId}/ai/ai-requests/
 */
import { apiRequest } from '../utils/apiClient';
import type {
  ClinicalDecisionSupportRequest,
  ClinicalDecisionSupportResponse,
  NLPSummarizationRequest,
  NLPSummarizationResponse,
  AutomatedCodingRequest,
  AutomatedCodingResponse,
  DrugInteractionCheckRequest,
  DrugInteractionCheckResponse,
  AIRequest,
} from '../types/ai';

/**
 * Get clinical decision support (diagnosis suggestions, treatment recommendations)
 */
export async function getClinicalDecisionSupport(
  visitId: string,
  request: ClinicalDecisionSupportRequest
): Promise<ClinicalDecisionSupportResponse> {
  return apiRequest<ClinicalDecisionSupportResponse>(
    `/visits/${visitId}/ai/clinical-decision-support/`,
    {
      method: 'POST',
      body: JSON.stringify(request),
    }
  );
}

/**
 * Summarize clinical notes using NLP
 */
export async function summarizeClinicalNotes(
  visitId: string,
  request: NLPSummarizationRequest
): Promise<NLPSummarizationResponse> {
  return apiRequest<NLPSummarizationResponse>(
    `/visits/${visitId}/ai/nlp-summarize/`,
    {
      method: 'POST',
      body: JSON.stringify(request),
    }
  );
}

/**
 * Generate ICD-11 and CPT codes from clinical notes
 */
export async function generateMedicalCodes(
  visitId: string,
  request: AutomatedCodingRequest
): Promise<AutomatedCodingResponse> {
  return apiRequest<AutomatedCodingResponse>(
    `/visits/${visitId}/ai/automated-coding/`,
    {
      method: 'POST',
      body: JSON.stringify(request),
    }
  );
}

/**
 * Check for drug interactions
 */
export async function checkDrugInteractions(
  visitId: string,
  request: DrugInteractionCheckRequest
): Promise<DrugInteractionCheckResponse> {
  return apiRequest<DrugInteractionCheckResponse>(
    `/visits/${visitId}/ai/drug-interaction-check/`,
    {
      method: 'POST',
      body: JSON.stringify(request),
    }
  );
}

/**
 * Get AI request history for a visit
 */
export async function getAIRequestHistory(visitId: string): Promise<AIRequest[]> {
  return apiRequest<AIRequest[]>(`/visits/${visitId}/ai/ai-requests/`);
}

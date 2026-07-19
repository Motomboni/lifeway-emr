/**
 * Clinical AI Scribe API — generate note with NHIA/ICD-11 validation.
 */
import { apiRequest } from '../utils/apiClient';
import type { GenerateScribeNoteResponse } from '../utils/scribeParser';
import type { ClinicalNoteType } from '../components/ai/AINotesPanel';

export interface GenerateScribeNoteRequest {
  transcript: string;
  note_type: ClinicalNoteType;
  visit_id?: number;
  appointment_id?: number | null;
}

export async function generateScribeNote(
  body: GenerateScribeNoteRequest
): Promise<GenerateScribeNoteResponse> {
  return apiRequest<GenerateScribeNoteResponse>('/ai/generate-note/', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export interface NHIATariff {
  id: number;
  nhia_code: string;
  name: string;
  description: string;
  category: string;
  amount_ngn: string;
  icd11_codes: string[];
  keywords: string;
  is_active: boolean;
}

export async function searchNHIATariffs(params: {
  search?: string;
  icd11?: string;
  nhia?: string;
}): Promise<NHIATariff[]> {
  const query = new URLSearchParams();
  if (params.search) query.set('search', params.search);
  if (params.icd11) query.set('icd11', params.icd11);
  if (params.nhia) query.set('nhia', params.nhia);
  const qs = query.toString();
  return apiRequest<NHIATariff[]>(`/billing/nhia-tariffs/${qs ? `?${qs}` : ''}`);
}

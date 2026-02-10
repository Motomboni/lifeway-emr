/**
 * AI Integration Types
 */

export type AIFeatureType = 
  | 'clinical_decision_support'
  | 'nlp_summarization'
  | 'automated_coding'
  | 'drug_interaction_check'
  | 'diagnosis_suggestion'
  | 'documentation_assistance'
  | 'image_analysis';

export type AIProvider = 'openai' | 'anthropic' | 'local' | 'azure_openai';

export interface AIRequest {
  id: number;
  visit_id: number;
  user: number;
  user_role: string;
  feature_type: AIFeatureType;
  feature_type_display: string;
  provider: AIProvider;
  provider_display: string;
  model_name: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: string;
  success: boolean;
  error_message?: string;
  response_time_ms?: number;
  timestamp: string;
}

export interface ClinicalDecisionSupportRequest {
  consultation_id?: number;
  patient_symptoms?: string;
  patient_history?: string;
  current_medications?: string[];
  include_differential_diagnosis?: boolean;
  include_treatment_suggestions?: boolean;
}

export interface SuggestedDiagnosis {
  diagnosis: string;
  confidence: number;
  icd11_code?: string;
  description?: string;
}

export interface TreatmentSuggestion {
  treatment: string;
  rationale?: string;
  dosage?: string;
  duration?: string;
}

export interface ClinicalDecisionSupportResponse {
  suggested_diagnoses: SuggestedDiagnosis[];
  differential_diagnosis?: SuggestedDiagnosis[];
  treatment_suggestions?: TreatmentSuggestion[];
  warnings?: string[];
  request_id: number;
  raw_response?: string; // Temporary for development
}

export interface NLPSummarizationRequest {
  consultation_id?: number;
  text?: string;
  summary_type?: 'brief' | 'detailed' | 'structured';
}

export interface NLPSummarizationResponse {
  summary: string;
  key_points?: string[];
  request_id: number;
}

export interface AutomatedCodingRequest {
  consultation_id: number;
  code_types?: ('icd11' | 'cpt')[];
}

export interface MedicalCode {
  code: string;
  description: string;
  confidence?: number;
}

export interface AutomatedCodingResponse {
  icd11_codes?: MedicalCode[];
  cpt_codes?: MedicalCode[];
  request_id: number;
  raw_response?: string; // Temporary for development
}

export interface DrugInteractionCheckRequest {
  current_medications: string[];
  new_medication: string;
}

export type InteractionSeverity = 'mild' | 'moderate' | 'severe' | 'contraindicated';

export interface DrugInteractionCheckResponse {
  has_interaction: boolean;
  severity?: InteractionSeverity;
  description?: string;
  recommendations?: string[];
  request_id: number;
  raw_response?: string; // Temporary for development
}

/**
 * Guide API — onboarding progress, workflows, Ask Guide, sandbox visits.
 */
import { apiRequest } from '../utils/apiClient';
import type {
  AskGuideResponse,
  GuideAnalyticsSummary,
  GuideProgressUpdate,
  SandboxVisitResponse,
  UserGuideProgress,
  VisitWorkflowResponse,
} from '../types/guide';

export async function fetchGuideProgress(): Promise<UserGuideProgress> {
  return apiRequest<UserGuideProgress>('/guide/me/progress/');
}

export async function updateGuideProgress(
  update: GuideProgressUpdate
): Promise<UserGuideProgress> {
  return apiRequest<UserGuideProgress>('/guide/me/progress/', {
    method: 'PATCH',
    body: JSON.stringify(update),
  });
}

export async function askGuide(query: string): Promise<AskGuideResponse> {
  return apiRequest<AskGuideResponse>('/guide/me/ask/', {
    method: 'POST',
    body: JSON.stringify({ query }),
  });
}

export async function fetchVisitWorkflow(visitId: number): Promise<VisitWorkflowResponse> {
  return apiRequest<VisitWorkflowResponse>(`/guide/visits/${visitId}/workflow/`);
}

export async function syncVisitWorkflow(
  visitId: number,
  packId: string,
  action: 'sync' | 'complete' | 'skip' = 'sync',
  stepId?: string
): Promise<VisitWorkflowResponse> {
  return apiRequest<VisitWorkflowResponse>(`/guide/visits/${visitId}/workflow/sync/`, {
    method: 'POST',
    body: JSON.stringify({ pack_id: packId, action, step_id: stepId }),
  });
}

export async function createSandboxVisit(): Promise<SandboxVisitResponse> {
  return apiRequest<SandboxVisitResponse>('/guide/sandbox-visit/', {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

export async function logGuideEvent(payload: {
  event_type: string;
  article_id?: string;
  target_id?: string;
  hint_id?: string;
  metadata?: Record<string, unknown>;
}): Promise<void> {
  await apiRequest('/guide/events/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function fetchGuideAnalytics(days = 30): Promise<GuideAnalyticsSummary> {
  return apiRequest<GuideAnalyticsSummary>(`/guide/analytics/?days=${days}`);
}

/** Types for the interactive Guide / digital adoption assistant. */

export interface UserGuideProgress {
  completed_steps: string[];
  dismissed_hints: string[];
  role_launch_completed: Record<string, boolean>;
  guide_preferences: GuidePreferences;
  guide_modules?: Record<string, boolean>;
  updated_at: string;
}

export interface GuidePreferences {
  enabled?: boolean;
  reduced_motion?: boolean;
}

export interface GuideProgressUpdate {
  step_id?: string;
  hint_id?: string;
  role_launch_role?: string;
  preferences?: Partial<GuidePreferences>;
}

export interface AskGuideResponse {
  query: string;
  answer: string;
  articles: Array<{
    id: string;
    title: string;
    summary: string;
    guide_target: string | null;
  }>;
  guide_target: string | null;
}

export type WorkflowStepStatus = 'completed' | 'active' | 'pending' | 'skipped';

export interface WorkflowStep {
  id: string;
  label: string;
  guide_target: string;
  status: WorkflowStepStatus;
}

export interface WorkflowPack {
  pack_id: string;
  title: string;
  steps: WorkflowStep[];
  completed_count: number;
  total_count: number;
}

export interface VisitWorkflowResponse {
  visit_id: number;
  workflows: WorkflowPack[];
}

export interface SandboxVisitResponse {
  visit_id: number;
  patient_id: number;
  message: string;
}

export interface RoleLaunchStep {
  id: string;
  title: string;
  body: string;
  guide_target: string;
  /** Optional module gate — hidden when org disables the module. */
  module?: string;
  /** Static route to open before highlighting (e.g. /dashboard). */
  route?: string;
  /** Open a sandbox visit before highlighting (consultation, nursing, billing). */
  requiresSandbox?: boolean;
  /** Path under /visits/:id when using sandbox (default inferred from role). */
  sandboxPath?: 'consultation' | 'nursing' | 'visit-details';
}

export interface SpotlightState {
  targetId: string;
  title: string;
  body: string;
  stepIndex?: number;
  stepTotal?: number;
  isRoleLaunch?: boolean;
  onNext?: () => void;
  onComplete?: () => void;
}

export interface JitHint {
  id: string;
  message: string;
  guide_target?: string;
  actionLabel?: string;
}

export interface GuideAnalyticsSummary {
  days: number;
  totals: Record<string, number>;
  top_articles: Array<{ article_id: string; count: number }>;
  events_by_role: Record<string, number>;
  unique_users: number;
  total_events: number;
}

export interface ConsultationMacro {
  trigger: string;
  label: string;
  expansion: Partial<{
    history: string;
    examination: string;
    diagnosis: string;
    clinical_notes: string;
  }>;
}

export interface GuideCommand {
  id: string;
  label: string;
  keywords: string[];
  roles?: string[];
  module?: string;
  action: 'navigate' | 'guide' | 'macro' | 'sandbox';
  path?: string;
  guideTarget?: string;
  macroTrigger?: string;
}

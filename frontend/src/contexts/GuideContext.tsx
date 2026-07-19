/**
 * Guide context — onboarding progress, help drawer, spotlight, and role launch.
 */
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import {
  createSandboxVisit,
  fetchGuideProgress,
  logGuideEvent,
  updateGuideProgress,
} from '../api/guide';
import { normalizeGuideModules } from '../data/guideModules';
import { getGuideTargetMeta } from '../data/guideTargetMeta';
import { getRoleLaunchSteps } from '../data/roleLaunchSteps';
import { useAuth } from './AuthContext';
import { isStaffUser } from '../utils/roleUtils';
import type { GuideModules } from '../data/guideModules';
import type { SpotlightState, UserGuideProgress } from '../types/guide';
import { waitForGuideTarget } from '../utils/guideDom';

interface GuideContextType {
  progress: UserGuideProgress | null;
  loading: boolean;
  drawerOpen: boolean;
  spotlight: SpotlightState | null;
  guideEnabled: boolean;
  roleLaunchActive: boolean;
  roleLaunchStepIndex: number;
  roleLaunchWelcomeOpen: boolean;
  sandboxVisitId: number | null;
  sandboxLoading: boolean;
  isRoleLaunchComplete: boolean;
  openDrawer: () => void;
  closeDrawer: () => void;
  toggleDrawer: () => void;
  showSpotlight: (state: SpotlightState) => void;
  showSpotlightForTarget: (
    targetId: string,
    title?: string,
    body?: string,
    options?: { stepIndex?: number; stepTotal?: number }
  ) => Promise<void>;
  clearSpotlight: () => void;
  dismissHint: (hintId: string) => Promise<void>;
  refreshProgress: () => Promise<void>;
  ensureSandboxVisit: () => Promise<number | null>;
  startRoleLaunch: () => void;
  resumeRoleLaunch: () => void;
  dismissRoleLaunchWelcome: () => void;
  setRoleLaunchStepIndex: (index: number) => void;
  recordRoleLaunchStep: (stepId: string) => Promise<void>;
  finishRoleLaunch: () => Promise<void>;
  skipRoleLaunch: () => Promise<void>;
  getRoleLaunchResumeIndex: () => number;
  guideModules: GuideModules;
}

const GuideContext = createContext<GuideContextType | undefined>(undefined);

function computeResumeIndex(
  role: string | undefined,
  progress: UserGuideProgress | null,
  modules?: GuideModules
): number {
  const steps = getRoleLaunchSteps(role, modules);
  if (steps.length === 0) return 0;
  const completed = new Set(progress?.completed_steps ?? []);
  const firstIncomplete = steps.findIndex((step) => !completed.has(step.id));
  return firstIncomplete >= 0 ? firstIncomplete : 0;
}

export function GuideProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, user } = useAuth();
  const [progress, setProgress] = useState<UserGuideProgress | null>(null);
  const [loading, setLoading] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [spotlight, setSpotlight] = useState<SpotlightState | null>(null);
  const [roleLaunchActive, setRoleLaunchActive] = useState(false);
  const [roleLaunchStepIndex, setRoleLaunchStepIndex] = useState(0);
  const [roleLaunchWelcomeOpen, setRoleLaunchWelcomeOpen] = useState(false);
  const [sandboxVisitId, setSandboxVisitId] = useState<number | null>(null);
  const [sandboxLoading, setSandboxLoading] = useState(false);
  const [welcomeDismissedSession, setWelcomeDismissedSession] = useState(false);

  const staffActive = isAuthenticated && isStaffUser(user);
  const guideEnabled = progress?.guide_preferences?.enabled !== false;
  const guideModules = useMemo(
    () => normalizeGuideModules(progress?.guide_modules),
    [progress?.guide_modules]
  );
  const isRoleLaunchComplete =
    !user?.role || progress?.role_launch_completed?.[user.role] === true;

  const getRoleLaunchResumeIndex = useCallback(
    () => computeResumeIndex(user?.role, progress, guideModules),
    [user?.role, progress, guideModules]
  );

  const refreshProgress = useCallback(async () => {
    if (!staffActive) {
      setProgress(null);
      return;
    }
    setLoading(true);
    try {
      const data = await fetchGuideProgress();
      setProgress(data);
    } catch {
      setProgress(null);
    } finally {
      setLoading(false);
    }
  }, [staffActive]);

  useEffect(() => {
    refreshProgress();
  }, [refreshProgress]);

  const openDrawer = useCallback(() => setDrawerOpen(true), []);
  const closeDrawer = useCallback(() => setDrawerOpen(false), []);
  const toggleDrawer = useCallback(() => setDrawerOpen((open) => !open), []);
  const clearSpotlight = useCallback(() => setSpotlight(null), []);

  const showSpotlight = useCallback((state: SpotlightState) => {
    setDrawerOpen(false);
    setSpotlight(state);
  }, []);

  const showSpotlightForTarget = useCallback(
    async (
      targetId: string,
      title?: string,
      body?: string,
      options?: { stepIndex?: number; stepTotal?: number }
    ) => {
      const meta = getGuideTargetMeta(targetId);
      const reducedMotion = progress?.guide_preferences?.reduced_motion === true;
      await waitForGuideTarget(targetId);
      if (reducedMotion) {
        document.querySelector(`[data-guide-id="${targetId}"]`)?.scrollIntoView({
          behavior: 'auto',
          block: 'center',
        });
      }
      showSpotlight({
        targetId,
        title: title ?? meta.title,
        body: body ?? meta.body,
        stepIndex: options?.stepIndex,
        stepTotal: options?.stepTotal,
      });
      void logGuideEvent({ event_type: 'spotlight', target_id: targetId }).catch(() => {});
    },
    [progress?.guide_preferences?.reduced_motion, showSpotlight]
  );

  const dismissHint = useCallback(async (hintId: string) => {
    const updated = await updateGuideProgress({ hint_id: hintId });
    setProgress(updated);
  }, []);

  const ensureSandboxVisit = useCallback(async (): Promise<number | null> => {
    if (sandboxVisitId != null) {
      return sandboxVisitId;
    }
    setSandboxLoading(true);
    try {
      const result = await createSandboxVisit();
      setSandboxVisitId(result.visit_id);
      return result.visit_id;
    } catch {
      return null;
    } finally {
      setSandboxLoading(false);
    }
  }, [sandboxVisitId]);

  const finishRoleLaunch = useCallback(async () => {
    if (!user?.role) return;
    try {
      const updated = await updateGuideProgress({ role_launch_role: user.role });
      setProgress(updated);
    } catch {
      // keep local state in sync even if API fails
    }
    setRoleLaunchActive(false);
    setRoleLaunchWelcomeOpen(false);
    clearSpotlight();
  }, [user?.role, clearSpotlight]);

  const skipRoleLaunch = useCallback(async () => {
    await finishRoleLaunch();
  }, [finishRoleLaunch]);

  const recordRoleLaunchStep = useCallback(async (stepId: string) => {
    try {
      const updated = await updateGuideProgress({ step_id: stepId });
      setProgress(updated);
    } catch {
      // non-blocking
    }
  }, []);

  const beginRoleLaunch = useCallback(() => {
    setRoleLaunchWelcomeOpen(false);
    setRoleLaunchStepIndex(computeResumeIndex(user?.role, progress, guideModules));
    setRoleLaunchActive(true);
  }, [user?.role, progress, guideModules]);

  const startRoleLaunch = beginRoleLaunch;
  const resumeRoleLaunch = useCallback(() => {
    closeDrawer();
    beginRoleLaunch();
  }, [closeDrawer, beginRoleLaunch]);

  const dismissRoleLaunchWelcome = useCallback(() => {
    setRoleLaunchWelcomeOpen(false);
    setWelcomeDismissedSession(true);
  }, []);

  useEffect(() => {
    if (loading || !staffActive || !user?.role || welcomeDismissedSession) return;
    if (isRoleLaunchComplete) return;
    if (roleLaunchActive || roleLaunchWelcomeOpen) return;
    if (getRoleLaunchSteps(user.role, guideModules).length === 0) return;

    const timer = window.setTimeout(() => {
      setRoleLaunchWelcomeOpen(true);
    }, 600);

    return () => window.clearTimeout(timer);
  }, [
    loading,
    staffActive,
    user?.role,
    isRoleLaunchComplete,
    roleLaunchActive,
    roleLaunchWelcomeOpen,
    welcomeDismissedSession,
    guideModules,
  ]);

  const value = useMemo<GuideContextType>(
    () => ({
      progress,
      loading,
      drawerOpen,
      spotlight,
      guideEnabled,
      roleLaunchActive,
      roleLaunchStepIndex,
      roleLaunchWelcomeOpen,
      sandboxVisitId,
      sandboxLoading,
      isRoleLaunchComplete,
      openDrawer,
      closeDrawer,
      toggleDrawer,
      showSpotlight,
      showSpotlightForTarget,
      clearSpotlight,
      dismissHint,
      refreshProgress,
      ensureSandboxVisit,
      startRoleLaunch,
      resumeRoleLaunch,
      dismissRoleLaunchWelcome,
      setRoleLaunchStepIndex,
      recordRoleLaunchStep,
      finishRoleLaunch,
      skipRoleLaunch,
      getRoleLaunchResumeIndex,
      guideModules,
    }),
    [
      progress,
      loading,
      drawerOpen,
      spotlight,
      guideEnabled,
      roleLaunchActive,
      roleLaunchStepIndex,
      roleLaunchWelcomeOpen,
      sandboxVisitId,
      sandboxLoading,
      isRoleLaunchComplete,
      openDrawer,
      closeDrawer,
      toggleDrawer,
      showSpotlight,
      showSpotlightForTarget,
      clearSpotlight,
      dismissHint,
      refreshProgress,
      ensureSandboxVisit,
      startRoleLaunch,
      resumeRoleLaunch,
      dismissRoleLaunchWelcome,
      recordRoleLaunchStep,
      finishRoleLaunch,
      skipRoleLaunch,
      getRoleLaunchResumeIndex,
      guideModules,
    ]
  );

  return <GuideContext.Provider value={value}>{children}</GuideContext.Provider>;
}

export function useGuide(): GuideContextType {
  const context = useContext(GuideContext);
  if (!context) {
    throw new Error('useGuide must be used within GuideProvider');
  }
  return context;
}

/**
 * RoleLaunchTour — orchestrates role-specific onboarding spotlights.
 */
import React, { useCallback, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useGuide } from '../../contexts/GuideContext';
import { getRoleLaunchSteps } from '../../data/roleLaunchSteps';
import {
  getSandboxLandingPath,
  isOnRoleLaunchPath,
  resolveRoleLaunchPath,
} from '../../utils/roleLaunchPaths';
import { waitForGuideTarget } from '../../utils/guideDom';
import RoleLaunchWelcome from './RoleLaunchWelcome';

export default function RoleLaunchTour() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const {
    roleLaunchActive,
    roleLaunchStepIndex,
    roleLaunchWelcomeOpen,
    sandboxVisitId,
    showSpotlight,
    clearSpotlight,
    ensureSandboxVisit,
    setRoleLaunchStepIndex,
    recordRoleLaunchStep,
    finishRoleLaunch,
    dismissRoleLaunchWelcome,
    guideModules,
  } = useGuide();

  const displayingRef = useRef(false);
  const displayedKeyRef = useRef<string | null>(null);

  const openSandboxPractice = useCallback(async () => {
    dismissRoleLaunchWelcome();
    clearSpotlight();
    const visitId = await ensureSandboxVisit();
    if (!visitId) return;
    navigate(getSandboxLandingPath(visitId, user?.role));
  }, [clearSpotlight, dismissRoleLaunchWelcome, ensureSandboxVisit, navigate, user?.role]);

  const displayStep = useCallback(
    async (index: number) => {
      if (!user?.role || displayingRef.current) return;

      const steps = getRoleLaunchSteps(user.role, guideModules);
      if (index >= steps.length) {
        await finishRoleLaunch();
        return;
      }

      const step = steps[index];
      displayingRef.current = true;

      try {
        let sandboxId = sandboxVisitId;
        if (step.requiresSandbox) {
          sandboxId = await ensureSandboxVisit();
          if (!sandboxId) {
            return;
          }
        }

        const targetPath = resolveRoleLaunchPath(step, sandboxId, user.role);
        if (targetPath && !isOnRoleLaunchPath(location.pathname, targetPath)) {
          navigate(targetPath);
          return;
        }

        await waitForGuideTarget(step.guide_target);

        const isLast = index === steps.length - 1;

        const advance = async () => {
          clearSpotlight();
          await recordRoleLaunchStep(step.id);
          setRoleLaunchStepIndex(index + 1);
        };

        showSpotlight({
          targetId: step.guide_target,
          title: step.title,
          body: step.body,
          stepIndex: index,
          stepTotal: steps.length,
          isRoleLaunch: true,
          onNext: isLast
            ? undefined
            : () => {
                void advance();
              },
          onComplete: isLast
            ? () => {
                void (async () => {
                  await recordRoleLaunchStep(step.id);
                  await finishRoleLaunch();
                })();
              }
            : undefined,
        });
      } finally {
        displayingRef.current = false;
      }
    },
    [
      user?.role,
      sandboxVisitId,
      location.pathname,
      ensureSandboxVisit,
      navigate,
      showSpotlight,
      clearSpotlight,
      recordRoleLaunchStep,
      setRoleLaunchStepIndex,
      finishRoleLaunch,
      guideModules,
    ]
  );

  useEffect(() => {
    if (!roleLaunchActive || !user?.role) {
      displayedKeyRef.current = null;
      return;
    }
    const key = `${roleLaunchStepIndex}:${location.pathname}`;
    if (displayedKeyRef.current === key) return;
    displayedKeyRef.current = key;
    void displayStep(roleLaunchStepIndex);
  }, [roleLaunchActive, roleLaunchStepIndex, location.pathname, user?.role, displayStep]);

  if (roleLaunchWelcomeOpen) {
    return <RoleLaunchWelcome onPracticeSandbox={() => void openSandboxPractice()} />;
  }

  return null;
}

export function useGuideSandboxNavigation() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { ensureSandboxVisit, closeDrawer, dismissRoleLaunchWelcome, clearSpotlight } = useGuide();

  const openSandboxPractice = useCallback(async () => {
    dismissRoleLaunchWelcome();
    clearSpotlight();
    closeDrawer();
    const visitId = await ensureSandboxVisit();
    if (!visitId) return null;
    navigate(getSandboxLandingPath(visitId, user?.role));
    return visitId;
  }, [
    clearSpotlight,
    closeDrawer,
    dismissRoleLaunchWelcome,
    ensureSandboxVisit,
    navigate,
    user?.role,
  ]);

  return { openSandboxPractice };
}

/**
 * useGuideJitHints — evaluates JIT rules and returns the highest-priority active hint.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { GUIDE_JIT_RULES, sortJitRulesByPriority, type GuideJitRule } from '../data/guideJitRules';
import { useAuth } from '../contexts/AuthContext';
import { useGuide } from '../contexts/GuideContext';
import { useGuidePage } from '../contexts/GuidePageContext';
import type { JitHint } from '../types/guide';
import {
  getPinnedVisitId,
  isGuideTargetInViewport,
  setPinnedVisitId,
} from '../utils/guideDom';

const PAID_STATUSES = new Set(['PAID', 'SETTLED', 'PARTIALLY_PAID']);

interface RouteEvent {
  path: string;
  at: number;
}

function isPaidStatus(status: string | undefined): boolean {
  if (!status) return false;
  return PAID_STATUSES.has(status);
}

function matchesRole(rule: GuideJitRule, role: string | undefined): boolean {
  if (!rule.roles || rule.roles.length === 0) return true;
  if (!role) return false;
  return rule.roles.includes(role) || role === 'ADMIN';
}

function matchesRoute(rule: GuideJitRule, pathname: string): boolean {
  if (!rule.routePrefix) return true;
  return pathname.startsWith(rule.routePrefix);
}

function countPingPong(events: RouteEvent[], a: string, b: string, windowMs: number): number {
  const cutoff = Date.now() - windowMs;
  const recent = events.filter((event) => event.at >= cutoff);
  let count = 0;
  for (let i = 1; i < recent.length; i += 1) {
    const prev = recent[i - 1].path;
    const curr = recent[i].path;
    const aPrev = prev.startsWith(a);
    const bPrev = prev.startsWith(b);
    const aCurr = curr.startsWith(a);
    const bCurr = curr.startsWith(b);
    if ((aPrev && bCurr) || (bPrev && aCurr)) {
      count += 1;
    }
  }
  return count;
}

function toJitHint(rule: GuideJitRule): JitHint {
  return {
    id: rule.id,
    message: rule.message,
    guide_target: rule.guide_target,
    actionLabel: rule.actionLabel,
  };
}

export function useGuideJitHints(): JitHint | null {
  const { user } = useAuth();
  const location = useLocation();
  const {
    progress,
    roleLaunchActive,
    roleLaunchWelcomeOpen,
    spotlight,
    drawerOpen,
  } = useGuide();
  const { pageState, pendingAskTarget } = useGuidePage();

  const [idleMs, setIdleMs] = useState(0);
  const [activeHint, setActiveHint] = useState<JitHint | null>(null);
  const routeEventsRef = useRef<RouteEvent[]>([]);
  const lastActivityRef = useRef(Date.now());
  const dismissedRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    dismissedRef.current = new Set(progress?.dismissed_hints ?? []);
  }, [progress?.dismissed_hints]);

  // Track route history for ping-pong detection
  useEffect(() => {
    const path = location.pathname;
    routeEventsRef.current.push({ path, at: Date.now() });
    if (routeEventsRef.current.length > 30) {
      routeEventsRef.current = routeEventsRef.current.slice(-30);
    }

    const consultationMatch = path.match(/\/visits\/(\d+)\/consultation/);
    if (consultationMatch) {
      setPinnedVisitId(consultationMatch[1]);
    }
  }, [location.pathname]);

  // Idle timer — reset on user activity
  useEffect(() => {
    const markActive = () => {
      lastActivityRef.current = Date.now();
      setIdleMs(0);
    };

    const events = ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart'] as const;
    events.forEach((event) => window.addEventListener(event, markActive, { passive: true }));

    const interval = window.setInterval(() => {
      setIdleMs(Date.now() - lastActivityRef.current);
    }, 1000);

    return () => {
      events.forEach((event) => window.removeEventListener(event, markActive));
      window.clearInterval(interval);
    };
  }, []);

  const isHintDismissed = useCallback((id: string) => dismissedRef.current.has(id), []);

  const evaluateRules = useCallback((): JitHint | null => {
    const role = user?.role;
    const pathname = location.pathname;
    const pinnedVisitId = getPinnedVisitId();

    const suppressed =
      roleLaunchActive ||
      roleLaunchWelcomeOpen ||
      !!spotlight ||
      drawerOpen;

    if (suppressed) return null;

    const candidates: GuideJitRule[] = [];

    for (const rule of GUIDE_JIT_RULES) {
      if (!matchesRole(rule, role)) continue;
      if (isHintDismissed(rule.id)) continue;

      switch (rule.type) {
        case 'payment_not_cleared': {
          if (!pathname.includes('/consultation')) break;
          if (!pageState.hasConsultation) break;
          if (isPaidStatus(pageState.paymentStatus)) break;
          if (pageState.paymentBlocked) {
            candidates.push(rule);
            break;
          }
          if (idleMs >= 60_000) {
            candidates.push(rule);
          }
          break;
        }
        case 'ask_guide_followup': {
          if (!pendingAskTarget) break;
          candidates.push({
            ...rule,
            guide_target: pendingAskTarget.targetId,
            message: pendingAskTarget.title
              ? `Still need help with "${pendingAskTarget.title}"?`
              : rule.message,
          });
          break;
        }
        case 'return_to_pinned_visit': {
          if (!matchesRoute(rule, pathname)) break;
          if (!pinnedVisitId) break;
          if (pathname.includes(`/visits/${pinnedVisitId}`)) break;
          if (idleMs < (rule.idleMs ?? 12_000)) break;
          candidates.push(rule);
          break;
        }
        case 'repeat_route_ping_pong': {
          const [a, b] = rule.pingPongRoutes ?? ['/dashboard', '/visits'];
          const threshold = rule.pingPongThreshold ?? 3;
          const windowMs = rule.pingPongWindowMs ?? 120_000;
          const count = countPingPong(routeEventsRef.current, a, b, windowMs);
          if (count >= threshold) {
            candidates.push(rule);
          }
          break;
        }
        case 'idle_lab_not_seen': {
          if (!pathname.includes('/consultation')) break;
          if (idleMs < (rule.idleMs ?? 25_000)) break;
          if (isGuideTargetInViewport('lab-inline')) break;
          candidates.push(rule);
          break;
        }
        default:
          break;
      }
    }

    const sorted = sortJitRulesByPriority(candidates);
    return sorted.length > 0 ? toJitHint(sorted[0]) : null;
  }, [
    user?.role,
    location.pathname,
    roleLaunchActive,
    roleLaunchWelcomeOpen,
    spotlight,
    drawerOpen,
    pageState,
    pendingAskTarget,
    idleMs,
    isHintDismissed,
  ]);

  useEffect(() => {
    const hint = evaluateRules();
    setActiveHint((prev) => {
      if (prev?.id === hint?.id && prev?.message === hint?.message) {
        return prev;
      }
      return hint;
    });
  }, [evaluateRules, idleMs, location.pathname]);

  return activeHint;
}

export function useGuideJitActions() {
  const navigate = useNavigate();
  const { dismissHint, showSpotlightForTarget, openDrawer } = useGuide();
  const { setPendingAskTarget, pageState } = useGuidePage();

  const executeHintAction = useCallback(
    async (hint: JitHint) => {
      if (hint.id === 'return-to-consultation') {
        const pinned = getPinnedVisitId();
        if (pinned) {
          navigate(`/visits/${pinned}/consultation`);
        }
        return;
      }

      if (hint.id === 'repeat-nav-visits') {
        openDrawer();
        return;
      }

      if (hint.id === 'payment-not-cleared') {
        const visitId = pageState.visitId ?? getPinnedVisitId();
        if (visitId) {
          navigate(`/visits/${visitId}`);
        } else if (hint.guide_target) {
          await showSpotlightForTarget(hint.guide_target);
        }
        return;
      }

      if (hint.guide_target) {
        await showSpotlightForTarget(hint.guide_target, hint.message);
      }

      if (hint.id === 'ask-guide-followup') {
        setPendingAskTarget(null);
      }
    },
    [navigate, openDrawer, pageState.visitId, setPendingAskTarget, showSpotlightForTarget]
  );

  const dismissJitHint = useCallback(
    async (hint: JitHint) => {
      if (hint.id === 'ask-guide-followup') {
        setPendingAskTarget(null);
      }
      await dismissHint(hint.id);
    },
    [dismissHint, setPendingAskTarget]
  );

  return { executeHintAction, dismissJitHint };
}

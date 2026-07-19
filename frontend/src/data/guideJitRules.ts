import type { JitHint } from '../types/guide';

export type GuideJitRuleType =
  | 'idle_lab_not_seen'
  | 'return_to_pinned_visit'
  | 'repeat_route_ping_pong'
  | 'payment_not_cleared'
  | 'ask_guide_followup';

export interface GuideJitRule extends JitHint {
  type: GuideJitRuleType;
  roles?: string[];
  /** Route must start with this prefix to evaluate the rule. */
  routePrefix?: string;
  idleMs?: number;
  /** For repeat_route_ping_pong — route prefixes to watch. */
  pingPongRoutes?: [string, string];
  pingPongThreshold?: number;
  /** Session window for ping-pong counting (ms). */
  pingPongWindowMs?: number;
  priority: number;
}

/** Lower priority number = shown first when multiple rules match. */
export const GUIDE_JIT_RULES: GuideJitRule[] = [
  {
    id: 'payment-not-cleared',
    type: 'payment_not_cleared',
    roles: ['DOCTOR'],
    routePrefix: '/visits/',
    message: 'Payment must be cleared before you can close this visit. Reception handles billing on Visit Details.',
    actionLabel: 'Go to visit details',
    guide_target: 'billing-dashboard',
    priority: 1,
  },
  {
    id: 'ask-guide-followup',
    type: 'ask_guide_followup',
    message: 'Want me to show that on screen?',
    actionLabel: 'Show me',
    priority: 2,
  },
  {
    id: 'return-to-consultation',
    type: 'return_to_pinned_visit',
    roles: ['DOCTOR'],
    routePrefix: '/dashboard',
    idleMs: 12_000,
    message: 'You have an open consultation in progress.',
    actionLabel: 'Return to visit',
    priority: 3,
  },
  {
    id: 'repeat-nav-visits',
    type: 'repeat_route_ping_pong',
    roles: ['DOCTOR', 'RECEPTIONIST'],
    pingPongRoutes: ['/dashboard', '/visits'],
    pingPongThreshold: 3,
    pingPongWindowMs: 120_000,
    message: 'Bouncing between screens? Tell Guide what you need — try "order lab" or "clear payment".',
    actionLabel: 'Open Guide',
    priority: 4,
  },
  {
    id: 'lab-order-idle',
    type: 'idle_lab_not_seen',
    roles: ['DOCTOR'],
    routePrefix: '/visits/',
    idleMs: 25_000,
    message: 'Looking for lab orders?',
    actionLabel: 'Show me',
    guide_target: 'lab-inline',
    priority: 5,
  },
];

export function getGuideJitRule(id: string): GuideJitRule | undefined {
  return GUIDE_JIT_RULES.find((rule) => rule.id === id);
}

export function sortJitRulesByPriority(rules: GuideJitRule[]): GuideJitRule[] {
  return [...rules].sort((a, b) => a.priority - b.priority);
}

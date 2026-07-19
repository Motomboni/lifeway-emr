/** DOM helpers for Guide spotlight targeting. */

const GUIDE_SELECTOR = (targetId: string) => `[data-guide-id="${targetId}"]`;

export function findGuideTarget(targetId: string): HTMLElement | null {
  return document.querySelector<HTMLElement>(GUIDE_SELECTOR(targetId));
}

export function scrollToGuideTarget(
  targetId: string,
  behavior: ScrollBehavior = 'smooth'
): HTMLElement | null {
  const el = findGuideTarget(targetId);
  if (!el) return null;
  el.scrollIntoView({ behavior, block: 'center', inline: 'nearest' });
  return el;
}

export interface GuideTargetRect {
  top: number;
  left: number;
  width: number;
  height: number;
}

export function getGuideTargetRect(targetId: string): GuideTargetRect | null {
  const el = findGuideTarget(targetId);
  if (!el) return null;
  const rect = el.getBoundingClientRect();
  if (rect.width === 0 && rect.height === 0) return null;
  return {
    top: rect.top,
    left: rect.left,
    width: rect.width,
    height: rect.height,
  };
}

/** True when any part of the guide target is visible in the viewport. */
export function isGuideTargetInViewport(targetId: string): boolean {
  const el = findGuideTarget(targetId);
  if (!el) return false;
  const rect = el.getBoundingClientRect();
  if (rect.width === 0 && rect.height === 0) return false;
  const vh = window.innerHeight || document.documentElement.clientHeight;
  const vw = window.innerWidth || document.documentElement.clientWidth;
  return rect.bottom > 0 && rect.right > 0 && rect.top < vh && rect.left < vw;
}

export const GUIDE_PINNED_VISIT_KEY = 'guide-pinned-visit';

export function getPinnedVisitId(): string | null {
  try {
    return sessionStorage.getItem(GUIDE_PINNED_VISIT_KEY);
  } catch {
    return null;
  }
}

export function setPinnedVisitId(visitId: string | number | null): void {
  try {
    if (visitId == null) {
      sessionStorage.removeItem(GUIDE_PINNED_VISIT_KEY);
    } else {
      sessionStorage.setItem(GUIDE_PINNED_VISIT_KEY, String(visitId));
    }
  } catch {
    // ignore storage errors
  }
}

/** Retry finding a target that mounts after route or role-gated render. */
export async function waitForGuideTarget(
  targetId: string,
  maxAttempts = 12,
  intervalMs = 120
): Promise<HTMLElement | null> {
  for (let i = 0; i < maxAttempts; i += 1) {
    const el = scrollToGuideTarget(targetId, i === 0 ? 'smooth' : 'auto');
    if (el) {
      const rect = el.getBoundingClientRect();
      if (rect.width > 0 || rect.height > 0) return el;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  return findGuideTarget(targetId);
}

import type { RoleLaunchStep } from '../types/guide';

/** Resolve navigation path for a role launch step (including sandbox visits). */
export function resolveRoleLaunchPath(
  step: RoleLaunchStep,
  sandboxVisitId: number | null,
  role: string
): string | null {
  if (step.route) {
    return step.route;
  }
  if (!step.requiresSandbox || sandboxVisitId == null) {
    return null;
  }

  const mode =
    step.sandboxPath ??
    (role === 'DOCTOR'
      ? 'consultation'
      : role === 'NURSE'
        ? 'nursing'
        : 'visit-details');

  switch (mode) {
    case 'consultation':
      return `/visits/${sandboxVisitId}/consultation`;
    case 'nursing':
      return `/visits/${sandboxVisitId}/nursing`;
    case 'visit-details':
      return `/visits/${sandboxVisitId}`;
    default:
      return null;
  }
}

/** Whether the current URL is ready for the step spotlight. */
export function isOnRoleLaunchPath(currentPath: string, expectedPath: string | null): boolean {
  if (!expectedPath) {
    return true;
  }
  if (currentPath === expectedPath) {
    return true;
  }
  // Allow nested routes (e.g. /visits/5/consultation matching /visits/5)
  if (expectedPath.startsWith('/visits/') && currentPath.startsWith(expectedPath)) {
    return true;
  }
  return currentPath.startsWith(`${expectedPath}/`);
}

/** Roles that can open a sandbox practice visit. */
export function roleSupportsSandbox(role: string | undefined): boolean {
  return role === 'DOCTOR' || role === 'NURSE' || role === 'RECEPTIONIST' || role === 'ADMIN';
}

export function getSandboxLandingPath(sandboxVisitId: number, role: string | undefined): string {
  if (role === 'DOCTOR') {
    return `/visits/${sandboxVisitId}/consultation`;
  }
  if (role === 'NURSE') {
    return `/visits/${sandboxVisitId}/nursing`;
  }
  return `/visits/${sandboxVisitId}`;
}

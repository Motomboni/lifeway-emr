/**
 * Resolve and persist the active clinic organization for API requests.
 */
import { setOrganizationId, getOrganizationId } from './apiClient';
import { getOrganizationMemberships } from '../api/organizations';

function orgIdFromAccessToken(access: string | null | undefined): number | null {
  if (!access) return null;
  try {
    const payload = access.split('.')[1];
    if (!payload) return null;
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=');
    const decoded = JSON.parse(atob(padded)) as { organization_id?: number };
    const id = decoded.organization_id;
    return typeof id === 'number' && !Number.isNaN(id) ? id : null;
  } catch {
    return null;
  }
}

/**
 * Ensure localStorage has a valid organization id for X-Organization-Id header.
 * Safe to call after login and when restoring a session.
 */
export async function ensureOrganizationContext(accessToken?: string | null): Promise<number | null> {
  const fromJwt = orgIdFromAccessToken(accessToken);
  if (fromJwt) {
    setOrganizationId(fromJwt);
    return fromJwt;
  }

  const existing = getOrganizationId();
  if (existing !== null) {
    return existing;
  }

  try {
    const memberships = await getOrganizationMemberships();
    const defaultMembership =
      memberships.find((m) => m.is_default) || memberships[0];
    const orgId = defaultMembership?.organization?.id ?? null;
    if (orgId) {
      setOrganizationId(orgId);
    }
    return orgId;
  } catch {
    return null;
  }
}

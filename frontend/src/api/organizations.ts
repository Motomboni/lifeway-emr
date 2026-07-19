/**
 * Organizations API — single-clinic Lifeway (org context for branding).
 */
import { apiRequest } from '../utils/apiClient';

export interface Organization {
  id: number;
  name: string;
  slug: string;
  logo_url?: string;
  email?: string;
  phone?: string;
  address?: string;
  patient_id_prefix: string;
  guide_modules?: Record<string, boolean>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface OrganizationMembership {
  id: number;
  organization: Organization;
  role: 'OWNER' | 'ADMIN' | 'MEMBER';
  is_default: boolean;
  created_at: string;
}

export async function getOrganizationMemberships(): Promise<OrganizationMembership[]> {
  const res = await apiRequest<OrganizationMembership[] | { results?: OrganizationMembership[] }>(
    '/organizations/memberships/'
  );
  return Array.isArray(res) ? res : (res?.results || []);
}

export async function getCurrentOrganization(): Promise<Organization | null> {
  try {
    return await apiRequest<Organization>('/organizations/me/');
  } catch {
    return null;
  }
}

export interface OrganizationMember {
  id: number;
  user_id: number;
  username: string;
  first_name: string;
  last_name: string;
  role: string;
  is_default: boolean;
}

export async function getOrganizationMembers(organizationId: number): Promise<OrganizationMember[]> {
  return apiRequest<OrganizationMember[]>(`/organizations/${organizationId}/members/`);
}

export async function updateOrganizationSettings(
  organizationId: number,
  data: Partial<
    Pick<
      Organization,
      'name' | 'logo_url' | 'email' | 'phone' | 'address' | 'patient_id_prefix' | 'guide_modules'
    >
  >
): Promise<Organization> {
  return apiRequest<Organization>(`/organizations/${organizationId}/settings/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function addOrganizationMemberByEmail(
  organizationId: number,
  email: string,
  role: 'ADMIN' | 'MEMBER' = 'MEMBER'
): Promise<void> {
  await apiRequest(`/organizations/${organizationId}/members/`, {
    method: 'POST',
    body: JSON.stringify({ email, role }),
  });
}

export async function addOrganizationMember(
  organizationId: number,
  userId: number,
  role: 'ADMIN' | 'MEMBER' = 'MEMBER'
): Promise<void> {
  await apiRequest(`/organizations/${organizationId}/members/`, {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, role }),
  });
}

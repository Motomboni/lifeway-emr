/**
 * Platform super-admin API (Django superuser only).
 */
import { apiRequest } from '../utils/apiClient';

export interface PlatformTotals {
  organizations: number;
  active_subscriptions: number;
  trial_subscriptions: number;
  patients: number;
  staff_memberships: number;
  mrr_ngn: string;
  revenue_30d_ngn: string;
}

export interface PlatformOverview {
  generated_at: string;
  totals: PlatformTotals;
  plan_breakdown: Array<{ plan__name: string; plan__slug: string; count: number }>;
  expiring_soon: Array<{
    organization_id: number;
    organization_name: string;
    organization_slug: string;
    plan: string;
    current_period_end: string | null;
    auto_renew_enabled: boolean;
  }>;
}

export interface PlatformOrganization {
  id: number;
  name: string;
  slug: string;
  email: string | null;
  created_at: string;
  subscription_status: string;
  plan_name: string | null;
  plan_slug: string | null;
  current_period_end: string | null;
  auto_renew_enabled: boolean;
  patients: number;
  users: number;
}

export async function getPlatformOverview(): Promise<PlatformOverview> {
  return apiRequest<PlatformOverview>('/platform/overview/');
}

export async function getPlatformOrganizations(): Promise<{
  count: number;
  organizations: PlatformOrganization[];
}> {
  return apiRequest('/platform/organizations/');
}

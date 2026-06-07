/**
 * Organizations API - Multi-tenancy / SaaS
 */
import { apiRequest, unauthenticatedRequest } from '../utils/apiClient';

export interface Organization {
  id: number;
  name: string;
  slug: string;
  logo_url?: string;
  email?: string;
  phone?: string;
  address?: string;
  patient_id_prefix: string;
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

/**
 * Get user's organization memberships (for tenant switcher)
 */
export async function getOrganizationMemberships(): Promise<OrganizationMembership[]> {
  const res = await apiRequest<OrganizationMembership[] | { results?: OrganizationMembership[] }>(
    '/organizations/memberships/'
  );
  return Array.isArray(res) ? res : (res?.results || []);
}

/**
 * Get current organization (from X-Organization-Id header context)
 */
export async function getCurrentOrganization(): Promise<Organization | null> {
  try {
    const org = await apiRequest<Organization>('/organizations/me/');
    return org;
  } catch {
    return null;
  }
}

/**
 * Set organization as default
 */
export async function setDefaultOrganization(organizationId: number): Promise<void> {
  await apiRequest(`/organizations/${organizationId}/set-default/`, {
    method: 'POST',
  });
}

/**
 * Self-serve organization signup (public, when ENABLE_ORG_SIGNUP=true).
 * Creates org + owner user + Starter subscription.
 */
export async function signupOrganization(data: {
  name: string;
  slug: string;
  email?: string;
  phone?: string;
  username: string;
  password: string;
  first_name: string;
  last_name: string;
}): Promise<{ organization: Organization; user: { id: number; username: string; first_name: string; last_name: string }; message: string }> {
  return unauthenticatedRequest('/organizations/signup/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Create a new organization (admin only)
 */
export async function createOrganization(data: {
  name: string;
  slug: string;
  email?: string;
  phone?: string;
  address?: string;
  patient_id_prefix?: string;
}): Promise<Organization> {
  return apiRequest<Organization>('/organizations/create/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
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

/**
 * List members of an organization
 */
export async function getOrganizationMembers(organizationId: number): Promise<OrganizationMember[]> {
  return apiRequest<OrganizationMember[]>(`/organizations/${organizationId}/members/`);
}

/**
 * Update clinic branding and contact (OWNER/ADMIN).
 */
export async function updateOrganizationSettings(
  organizationId: number,
  data: Partial<Pick<Organization, 'name' | 'logo_url' | 'email' | 'phone' | 'address' | 'patient_id_prefix'>>
): Promise<Organization> {
  return apiRequest<Organization>(`/organizations/${organizationId}/settings/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Add staff by email (must have registered first).
 */
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

/**
 * Get subscription status with usage and limits
 */
export interface SubscriptionStatus {
  plan: { name: string; slug: string; max_users: number | null; max_patients: number | null; price_monthly: string; currency: string } | null;
  status: string;
  payment_provider?: string;
  days_until_renewal?: number | null;
  current_period_end?: string | null;
  trial_ends_at?: string | null;
  auto_renew_enabled?: boolean;
  paystack_subscription_code?: string | null;
  usage: { patients: number; users: number };
  limits: {
    users: { current: number; max: number | null; at_limit: boolean };
    patients: { current: number; max: number | null; at_limit: boolean };
  };
}

export async function getSubscriptionStatus(): Promise<SubscriptionStatus | null> {
  try {
    return await apiRequest<SubscriptionStatus>('/subscriptions/status/');
  } catch {
    return null;
  }
}

/**
 * Get available subscription plans
 */
export interface Plan {
  id: number;
  name: string;
  slug: string;
  description: string;
  max_users: number | null;
  max_patients: number | null;
  max_storage_mb: number | null;
  price_monthly: string;
  price_yearly: string;
  currency: string;
  features: Record<string, boolean | string>;
  is_active: boolean;
}

export async function getPlans(): Promise<Plan[]> {
  const res = await apiRequest<Plan[] | { results?: Plan[] }>('/plans/');
  return Array.isArray(res) ? res : (res?.results || []);
}

/**
 * Initialize Paystack / Flutterwave checkout for plan upgrade.
 * Returns authorization URL to redirect user, or null if not configured.
 */
export async function createCheckoutSession(params: {
  plan_slug: string;
  success_url: string;
  cancel_url: string;
}): Promise<{ checkout_url: string } | null> {
  try {
    return await apiRequest<{ checkout_url: string }>('/subscriptions/checkout/', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  } catch {
    return null;
  }
}

/**
 * Verify SaaS subscription payment after Paystack/Flutterwave redirect.
 */
export async function verifySubscriptionPayment(reference: string): Promise<{
  detail: string;
  subscription?: SubscriptionStatus;
} | null> {
  try {
    return await apiRequest('/subscriptions/verify-payment/', {
      method: 'POST',
      body: JSON.stringify({ reference }),
    });
  } catch {
    return null;
  }
}

/**
 * Disable Paystack auto-renewal for the current subscription.
 */
export async function cancelSubscriptionAutoRenew(): Promise<{
  detail: string;
  subscription?: SubscriptionStatus;
}> {
  return apiRequest('/subscriptions/cancel-auto-renew/', {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

/**
 * Billing self-service portal (legacy Stripe only).
 */
export async function createPortalSession(params: {
  return_url: string;
}): Promise<{ portal_url: string } | null> {
  return apiRequest<{ portal_url: string }>('/subscriptions/portal/', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export interface SaasBillingInvoice {
  id: string;
  amount_due: number;
  amount_paid: number;
  currency: string;
  status: string;
  created: number;
  hosted_invoice_url: string | null;
  pdf: string | null;
  number: string | null;
  plan_name?: string;
  provider?: string;
}

/** @deprecated Use SaasBillingInvoice */
export type StripeInvoice = SaasBillingInvoice;

/**
 * Get recent SaaS subscription payment history.
 */
export async function getBillingInvoices(): Promise<SaasBillingInvoice[]> {
  try {
    return await apiRequest<SaasBillingInvoice[]>('/subscriptions/invoices/');
  } catch {
    return [];
  }
}


/**
 * Add a member to an organization
 */
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

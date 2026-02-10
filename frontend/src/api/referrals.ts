/**
 * API client for Referrals.
 */
import { apiRequest } from '../utils/apiClient';
import { Referral, ReferralCreate, ReferralUpdate } from '../types/referrals';

/**
 * Fetch referrals for a visit
 */
export async function fetchReferrals(visitId: number): Promise<Referral[]> {
  const data = await apiRequest<Referral[]>(
    `/visits/${visitId}/referrals/`
  );
  return Array.isArray(data) ? data : [];
}

/**
 * Fetch a single referral
 */
export async function getReferral(
  visitId: number,
  referralId: number
): Promise<Referral> {
  return apiRequest<Referral>(`/visits/${visitId}/referrals/${referralId}/`);
}

/**
 * Create a referral
 */
export async function createReferral(
  visitId: number,
  data: ReferralCreate
): Promise<Referral> {
  return apiRequest<Referral>(`/visits/${visitId}/referrals/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Update a referral
 */
export async function updateReferral(
  visitId: number,
  referralId: number,
  data: ReferralUpdate
): Promise<Referral> {
  return apiRequest<Referral>(`/visits/${visitId}/referrals/${referralId}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Accept a referral
 */
export async function acceptReferral(
  visitId: number,
  referralId: number
): Promise<Referral> {
  return apiRequest<Referral>(
    `/visits/${visitId}/referrals/${referralId}/accept/`,
    {
      method: 'POST',
    }
  );
}

/**
 * Complete a referral
 */
export async function completeReferral(
  visitId: number,
  referralId: number
): Promise<Referral> {
  return apiRequest<Referral>(
    `/visits/${visitId}/referrals/${referralId}/complete/`,
    {
      method: 'POST',
    }
  );
}

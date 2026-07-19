/**
 * Patient portal OTP helpers (requires E2E_OTP_EXPOSE=true on backend).
 */
import { Page } from '@playwright/test';
import {
  AUTH_REQUEST_OTP_URL,
  AUTH_VERIFY_OTP_URL,
  TEST_PATIENT,
} from './test-users';

interface OtpRequestResponse {
  success: boolean;
  debug_otp?: string;
  detail?: string;
  error?: string;
}

export async function requestPatientOtp(
  page: Page,
  email: string = TEST_PATIENT.email
): Promise<string> {
  const response = await page.request.post(AUTH_REQUEST_OTP_URL, {
    data: { email, channel: 'email' },
  });

  const body = (await response.json()) as OtpRequestResponse;
  if (!response.ok() || !body.success) {
    throw new Error(
      `OTP request failed (${response.status()}): ${body.detail || body.error || JSON.stringify(body)}`
    );
  }
  if (!body.debug_otp) {
    throw new Error(
      'debug_otp missing — set E2E_OTP_EXPOSE=true on the Django backend for E2E tests'
    );
  }
  return body.debug_otp;
}

export async function loginPatientViaOtp(page: Page, email: string = TEST_PATIENT.email) {
  const otp = await requestPatientOtp(page, email);

  const response = await page.request.post(AUTH_VERIFY_OTP_URL, {
    data: { email, otp_code: otp, device_type: 'web' },
  });

  const data = await response.json();
  if (!response.ok() || !data.success) {
    throw new Error(`OTP verify failed: ${JSON.stringify(data)}`);
  }

  await page.goto('/login', { waitUntil: 'commit', timeout: 30000 });
  await page.evaluate(
    ({ tokens, userData }) => {
      localStorage.setItem(
        'auth_tokens',
        JSON.stringify({ access: tokens.access, refresh: tokens.refresh })
      );
      localStorage.setItem('auth_user', JSON.stringify(userData));
      localStorage.setItem('auth_token', tokens.access);
    },
    { tokens: { access: data.access, refresh: data.refresh }, userData: data.user }
  );

  await page.goto('/patient-portal/dashboard', { waitUntil: 'commit', timeout: 30000 });
}

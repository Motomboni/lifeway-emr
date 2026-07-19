/**
 * E2E: Patient portal OTP login
 */
import { test, expect } from '@playwright/test';
import { skipIfServicesDown } from '../helpers/health';
import { loginPatientViaOtp } from '../helpers/otp';
import { TEST_PATIENT } from '../helpers/test-users';

test.describe('Patient portal OTP login', () => {
  test.beforeEach(async ({ baseURL, page }) => {
    await skipIfServicesDown(page, baseURL!);
  });

  test('patient reaches portal dashboard via OTP', async ({ page }) => {
    await loginPatientViaOtp(page, TEST_PATIENT.email);
    await expect(page).toHaveURL(/\/patient-portal\/dashboard/);
    await expect(page.getByRole('heading', { name: 'Patient Portal' })).toBeVisible({
      timeout: 15000,
    });
  });

  test('OTP login UI flow', async ({ page }) => {
    await page.goto('/otp-login', { waitUntil: 'commit' });
    await expect(page.getByRole('heading', { name: /patient portal/i })).toBeVisible();

    await page.getByLabel(/email address/i).fill(TEST_PATIENT.email);
    await page.getByRole('button', { name: /send login code/i }).click();

    await expect(page.getByRole('heading', { name: /enter code/i })).toBeVisible({
      timeout: 15000,
    });
  });
});

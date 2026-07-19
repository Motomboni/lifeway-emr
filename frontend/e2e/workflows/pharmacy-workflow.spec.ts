/**
 * E2E: Pharmacist prescription worklist access
 */
import { test, expect } from '@playwright/test';
import { loginAs } from '../helpers/auth';
import { skipIfServicesDown } from '../helpers/health';
import { TEST_PHARMACIST } from '../helpers/test-users';

test.describe('Pharmacy workflow', () => {
  test.beforeEach(async ({ baseURL, page }) => {
    await skipIfServicesDown(page, baseURL!);
  });

  test('pharmacist opens prescriptions worklist', async ({ page }) => {
    await loginAs(page, TEST_PHARMACIST);
    await page.goto('/prescriptions', { waitUntil: 'commit' });
    await expect(page.getByRole('heading', { name: 'Prescriptions' })).toBeVisible({
      timeout: 15000,
    });
    await expect(
      page.getByRole('heading', { name: /visits with prescriptions/i })
    ).toBeVisible();
  });
});

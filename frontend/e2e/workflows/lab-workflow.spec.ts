/**
 * E2E: Lab technician worklist access
 */
import { test, expect } from '@playwright/test';
import { loginAs } from '../helpers/auth';
import { skipIfServicesDown } from '../helpers/health';
import { TEST_LAB_TECH } from '../helpers/test-users';

test.describe('Lab workflow', () => {
  test.beforeEach(async ({ baseURL, page }) => {
    await skipIfServicesDown(page, baseURL!);
  });

  test('lab tech opens lab orders worklist', async ({ page }) => {
    await loginAs(page, TEST_LAB_TECH);
    await page.goto('/lab-orders', { waitUntil: 'commit' });
    await expect(page.getByRole('heading', { name: 'Lab Orders' })).toBeVisible({
      timeout: 15000,
    });
    await expect(page.getByRole('heading', { name: /visits with lab orders/i })).toBeVisible();
  });
});

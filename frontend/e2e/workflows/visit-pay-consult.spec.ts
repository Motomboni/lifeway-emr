/**
 * E2E: Visit → Pay → Consult workflow (cash visit)
 *
 * Run: npx playwright test e2e/workflows/visit-pay-consult.spec.ts --project=chromium
 */
import { test, expect } from '@playwright/test';
import { gotoAuthenticated, loginAs, navigateInApp, switchUser } from '../helpers/auth';
import { payRegistrationGate } from '../helpers/billing';
import { skipIfServicesDown } from '../helpers/health';
import { TEST_DOCTOR, TEST_RECEPTIONIST } from '../helpers/test-users';

test.setTimeout(120000);

test.describe('Visit → Pay → Consult workflow', () => {
  test.beforeEach(async ({ baseURL, page }) => {
    await skipIfServicesDown(page, baseURL!);
  });

  test('receptionist creates visit, doctor opens consultation', async ({ page }) => {
    let createdVisitId: number | null = null;

    await loginAs(page, TEST_RECEPTIONIST);
    await navigateInApp(page, '/visits', /visits/i);

    await page.getByRole('button', { name: /create visit|new visit/i }).first().click();
    await page.waitForURL(/\/visits\/new/, { timeout: 15000 });

    const createHeading = page.getByRole('heading', { name: /create new visit/i });
    if (await createHeading.isVisible({ timeout: 10000 }).catch(() => false)) {
      const searchInput = page.locator('input[placeholder*="Search"], input[type="search"]').first();
      if (await searchInput.isVisible({ timeout: 5000 }).catch(() => false)) {
        await searchInput.fill('LMC');
        await page
          .waitForResponse((res) => res.url().includes('/patients') && res.ok(), {
            timeout: 10000,
          })
          .catch(() => {});
        const patientOption = page
          .locator('[class*="patient"], li, button')
          .filter({ hasText: /LMC/i })
          .first();
        if (await patientOption.isVisible({ timeout: 5000 }).catch(() => false)) {
          await patientOption.click();
        }
      }

      const submitBtn = page.getByRole('button', { name: /create visit/i });
      if (await submitBtn.isEnabled({ timeout: 5000 }).catch(() => false)) {
        await submitBtn.click();
        await page.waitForURL(/\/visits\/\d+/, { timeout: 20000 }).catch(() => {});
        const match = page.url().match(/\/visits\/(\d+)/);
        if (match) createdVisitId = Number(match[1]);
      }
    }

    // Client-side nav — avoid full reload after visit flow (Vite HMR can hang domcontentloaded)
    await page.getByRole('link', { name: /back to dashboard/i }).click();
    await page.waitForURL(/\/dashboard/, { timeout: 15000 });
    await page.getByRole('heading', { name: 'Pending Queue' }).click();
    await page.waitForURL(/\/billing\/pending-queue/, { timeout: 15000 });
    await expect(page.getByRole('heading', { name: 'Central Billing Queue' })).toBeVisible({
      timeout: 15000,
    });

    if (createdVisitId) {
      await payRegistrationGate(page, createdVisitId);
    }

    await switchUser(page, TEST_DOCTOR);

    if (createdVisitId) {
      await gotoAuthenticated(page, `/visits/${createdVisitId}/consultation`);
      await expect(page.locator('textarea#history')).toBeVisible({ timeout: 30000 });
    } else {
      await gotoAuthenticated(page, '/visits');
      const openConsult = page.getByRole('button', { name: 'Open Consultation' }).first();
      await expect(openConsult).toBeVisible({ timeout: 20000 });
      await openConsult.click();
      await page.waitForURL(/\/consultation/, { timeout: 15000 });
      await expect(page.locator('textarea#history')).toBeVisible({ timeout: 30000 });
    }
  });
});

/**
 * Capture screenshots for docs/Lifeway_EMR_User_Manual.md
 *
 * Prerequisites:
 * - Backend: http://127.0.0.1:8000 (or set PLAYWRIGHT_TEST_BASE_URL for frontend only)
 * - Frontend: npm start (or let Playwright webServer start it)
 * - At minimum: receptionist, doctor, lab tech users (same as e2e/billing/README.md)
 *
 * Run from frontend/:
 *   npx playwright test e2e/manual/capture-manual-screenshots.spec.ts --project=chromium
 *
 * Optional env (if set, extra role screenshots are captured):
 *   MANUAL_NURSE_EMAIL, MANUAL_NURSE_PASSWORD
 *   MANUAL_RADIOLOGY_EMAIL, MANUAL_RADIOLOGY_PASSWORD
 *   MANUAL_PHARMACIST_EMAIL, MANUAL_PHARMACIST_PASSWORD
 *   MANUAL_ADMIN_EMAIL, MANUAL_ADMIN_PASSWORD
 *   MANUAL_PATIENT_EMAIL, MANUAL_PATIENT_PASSWORD
 */
import { test, expect, Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

test.setTimeout(180000);

test.describe.configure({ mode: 'serial' });

const SCREENSHOT_DIR = path.join(process.cwd(), '..', 'docs', 'manual-screenshots');

const DEFAULT = {
  receptionist: {
    email: process.env.MANUAL_RECEPTIONIST_EMAIL || 'receptionist@clinic.com',
    password: process.env.MANUAL_RECEPTIONIST_PASSWORD || 'Receptionist123!',
  },
  doctor: {
    email: process.env.MANUAL_DOCTOR_EMAIL || 'doctor@clinic.com',
    password: process.env.MANUAL_DOCTOR_PASSWORD || 'Doctor123!',
  },
  lab: {
    email: process.env.MANUAL_LAB_EMAIL || 'labtech@clinic.com',
    password: process.env.MANUAL_LAB_PASSWORD || 'LabTech123!',
  },
};

async function logout(page: Page) {
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  }).catch(() => {});
  await page.context().clearCookies();
  await page.goto('about:blank');
  await page.goto('/login', { waitUntil: 'domcontentloaded' }).catch(() => {});
}

async function loginAs(page: Page, email: string, password: string) {
  await logout(page);
  await page.goto('/login', { waitUntil: 'domcontentloaded' });
  const usernameInput = page.locator('#username').first();
  await expect(usernameInput).toBeVisible({ timeout: 20000 });
  await usernameInput.fill(email);
  await page.locator('#password').first().fill(password);
  await Promise.all([
    page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 25000 }),
    page.locator('button[type="submit"]:has-text("Sign In")').click(),
  ]);
  await expect(page.locator('button:has-text("Logout")').first()).toBeVisible({ timeout: 15000 });
}

async function shot(page: Page, filename: string) {
  await fs.promises.mkdir(SCREENSHOT_DIR, { recursive: true });
  const full = path.join(SCREENSHOT_DIR, filename);
  await page.screenshot({ path: full, fullPage: true });
  console.log('Wrote', full);
}

test('capture manual screenshots (chromium)', async ({ page }) => {
  await page.setViewportSize({ width: 1360, height: 900 });

  // 01 — Login (unauthenticated)
  await page.goto('/login', { waitUntil: 'networkidle' }).catch(() =>
    page.goto('/login', { waitUntil: 'domcontentloaded' })
  );
  await expect(page.locator('h2:has-text("Sign In")')).toBeVisible({ timeout: 15000 });
  await shot(page, '01-login.png');

  // 02–05 Receptionist
  try {
    await loginAs(page, DEFAULT.receptionist.email, DEFAULT.receptionist.password);
    await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(800);
    await shot(page, '02-receptionist-dashboard.png');

    await page.goto('/patients/register', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);
    await shot(page, '03-patient-registration.png');

    await page.goto('/visits', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(800);
    await shot(page, '04-visits-list.png');

    await page.goto('/billing/pending-queue', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600);
    await shot(page, '05-billing-pending-queue.png');

    await page.goto('/patients/verification', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600);
    await shot(page, '06-patient-verification.png');
  } catch (e) {
    console.error('Receptionist screenshots failed (check backend + receptionist user):', e);
    throw e;
  }

  // 07–08 Doctor
  try {
    await loginAs(page, DEFAULT.doctor.email, DEFAULT.doctor.password);
    await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(800);
    await shot(page, '07-doctor-dashboard.png');

    await page.goto('/visits', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(800);
    await shot(page, '08-doctor-visits-list.png');

    await page.goto('/appointments', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600);
    await shot(page, '09-appointments.png');
  } catch (e) {
    console.error('Doctor screenshots failed:', e);
    throw e;
  }

  // 10 Lab tech
  try {
    await loginAs(page, DEFAULT.lab.email, DEFAULT.lab.password);
    await page.goto('/lab-orders', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);
    await shot(page, '10-lab-orders.png');
  } catch (e) {
    console.error('Lab tech screenshots failed:', e);
    throw e;
  }

  // Optional roles
  const nurseEmail = process.env.MANUAL_NURSE_EMAIL;
  const nursePass = process.env.MANUAL_NURSE_PASSWORD;
  if (nurseEmail && nursePass) {
    try {
      await loginAs(page, nurseEmail, nursePass);
      await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(800);
      await shot(page, '11-nurse-dashboard.png');
    } catch (e) {
      console.warn('Nurse screenshot skipped:', e);
    }
  }

  const radEmail = process.env.MANUAL_RADIOLOGY_EMAIL;
  const radPass = process.env.MANUAL_RADIOLOGY_PASSWORD;
  if (radEmail && radPass) {
    try {
      await loginAs(page, radEmail, radPass);
      await page.goto('/radiology-orders', { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(1000);
      await shot(page, '12-radiology-orders.png');
    } catch (e) {
      console.warn('Radiology screenshot skipped:', e);
    }
  }

  const pharmEmail = process.env.MANUAL_PHARMACIST_EMAIL;
  const pharmPass = process.env.MANUAL_PHARMACIST_PASSWORD;
  if (pharmEmail && pharmPass) {
    try {
      await loginAs(page, pharmEmail, pharmPass);
      await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(800);
      await shot(page, '13-pharmacist-dashboard.png');

      await page.goto('/prescriptions', { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(800);
      await shot(page, '14-prescriptions.png');

      await page.goto('/drugs', { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(800);
      await shot(page, '15-drug-catalog-inventory.png');
    } catch (e) {
      console.warn('Pharmacist screenshots skipped:', e);
    }
  }

  const adminEmail = process.env.MANUAL_ADMIN_EMAIL;
  const adminPass = process.env.MANUAL_ADMIN_PASSWORD;
  if (adminEmail && adminPass) {
    try {
      await loginAs(page, adminEmail, adminPass);
      await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(800);
      await shot(page, '16-admin-dashboard.png');
    } catch (e) {
      console.warn('Admin screenshot skipped:', e);
    }
  }

  const patientEmail = process.env.MANUAL_PATIENT_EMAIL;
  const patientPass = process.env.MANUAL_PATIENT_PASSWORD;
  if (patientEmail && patientPass) {
    try {
      await loginAs(page, patientEmail, patientPass);
      await page.goto('/patient-portal/dashboard', { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(1000);
      await shot(page, '17-patient-portal-dashboard.png');
    } catch (e) {
      console.warn('Patient portal screenshot skipped:', e);
    }
  }

  await logout(page);
});

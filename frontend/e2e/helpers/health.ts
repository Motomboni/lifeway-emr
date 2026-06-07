import { test } from '@playwright/test';
import { BACKEND_HEALTH_URL } from './test-users';

/** Returns true when Django health endpoint responds OK. */
export async function isBackendHealthy(
  request: import('@playwright/test').APIRequestContext
): Promise<boolean> {
  try {
    const res = await request.get(BACKEND_HEALTH_URL, { timeout: 5000 });
    return res.ok();
  } catch {
    return false;
  }
}

/** Skip the current test when backend or frontend is unreachable. */
export async function skipIfServicesDown(page: import('@playwright/test').Page, baseURL: string) {
  const backend = await page.request.get(BACKEND_HEALTH_URL).catch(() => null);
  test.skip(!backend?.ok(), 'Backend not running on :8000');

  const frontend = await page.request.get(`${baseURL}/login`).catch(() => null);
  test.skip(!frontend?.ok(), `Frontend not running at ${baseURL}`);
}

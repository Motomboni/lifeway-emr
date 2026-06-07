/**
 * Playwright global setup — seed E2E users when the Django backend is up.
 */
import { execSync } from 'child_process';
import path from 'path';
import type { FullConfig } from '@playwright/test';

const BACKEND_HEALTH =
  process.env.PLAYWRIGHT_BACKEND_URL || 'http://127.0.0.1:8000/api/v1/health/';

async function globalSetup(_config: FullConfig) {
  try {
    const res = await fetch(BACKEND_HEALTH, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) {
      console.warn('[e2e] Backend health check failed — skipping seed_e2e_users');
      return;
    }
  } catch {
    console.warn(
      '[e2e] Backend not reachable at',
      BACKEND_HEALTH,
      '— start Django and run: python manage.py seed_e2e_users'
    );
    return;
  }

  // Playwright runs with cwd = frontend/
  const backendDir = path.resolve(process.cwd(), '../backend');
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      execSync('python manage.py seed_e2e_users', {
        cwd: backendDir,
        stdio: 'inherit',
        env: {
          ...process.env,
          DEBUG: process.env.DEBUG || 'True',
          SECRET_KEY:
            process.env.SECRET_KEY || 'ci-e2e-secret-key-not-for-production',
        },
      });
      return;
    } catch (err) {
      if (attempt < 2) {
        console.warn(`[e2e] seed_e2e_users attempt ${attempt + 1} failed, retrying...`);
        await new Promise((r) => setTimeout(r, 2000 * (attempt + 1)));
        continue;
      }
      console.warn('[e2e] seed_e2e_users failed:', err);
    }
  }
}

export default globalSetup;

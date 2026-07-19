/**

 * Shared Playwright auth helpers for Damianix EMR (SPA-aware).

 */

import { expect, Page } from '@playwright/test';

import { AUTH_LOGIN_URL, type TestUser } from './test-users';



interface LoginResponse {

  access: string;

  refresh: string;

  user: Record<string, unknown>;

  organizations?: Array<{

    is_default?: boolean;

    organization?: { id?: number };

  }>;

}



function authMeOk(res: { url: () => string; ok: () => boolean }) {

  return res.url().includes('/auth/me/') && res.ok();

}



/** Wait until JWT is in localStorage and we are not on /login. */

export async function ensureAuthenticated(page: Page) {

  if (!isAppOrigin(page.url())) {

    throw new Error(`ensureAuthenticated requires app origin, got: ${page.url()}`);

  }

  await page.waitForFunction(

    () =>

      localStorage.getItem('auth_tokens') !== null &&

      !window.location.pathname.includes('/login'),

    undefined,

    { timeout: 20000 }

  );

  await expect(page).not.toHaveURL(/\/login/);

}



/**

 * Navigate to a protected route and wait for session + optional heading.

 * Uses waitUntil: 'commit' — Vite dev server often never reaches domcontentloaded

 * (HMR websocket keeps the document "loading").

 */

export async function gotoAuthenticated(

  page: Page,

  path: string,

  heading?: RegExp | string

) {

  const authMe = page.waitForResponse(authMeOk, { timeout: 20000 });

  await page.goto(path, { waitUntil: 'commit', timeout: 30000 });

  await authMe.catch(() => {});

  await ensureAuthenticated(page);

  if (heading) {

    await expect(page.getByRole('heading', { name: heading }).first()).toBeVisible({

      timeout: 15000,

    });

  }

}



/**

 * SPA client-side navigation (no full document reload). Prefer after login.

 */

export async function navigateInApp(

  page: Page,

  path: string,

  heading?: RegExp | string

) {

  await page.evaluate((targetPath) => {

    window.history.pushState({}, '', targetPath);

    window.dispatchEvent(new PopStateEvent('popstate'));

  }, path);

  await page.waitForURL((url) => url.pathname === path || url.pathname.startsWith(path), {

    timeout: 15000,

  });

  await ensureAuthenticated(page);

  if (heading) {

    await expect(page.getByRole('heading', { name: heading }).first()).toBeVisible({

      timeout: 15000,

    });

  }

}



function seedSession(

  page: Page,

  data: LoginResponse,

  orgId: number | null

) {

  return page.evaluate(

    ({ tokens, userData, orgId: oid }) => {

      localStorage.setItem(

        'auth_tokens',

        JSON.stringify({ access: tokens.access, refresh: tokens.refresh })

      );

      localStorage.setItem('auth_user', JSON.stringify(userData));

      localStorage.setItem('auth_token', tokens.access);

      if (oid != null) {

        localStorage.setItem('organization_id', String(oid));

      } else {

        localStorage.removeItem('organization_id');

      }

    },

    {

      tokens: { access: data.access, refresh: data.refresh },

      userData: data.user,

      orgId,

    }

  );

}



/**

 * API login + seed localStorage (Playwright best practice — avoids UI flake and extra

 * round-trips). Still exercises the real auth endpoint and JWT flow.

 */

export async function loginViaApi(page: Page, user: Pick<TestUser, 'email' | 'password'>) {

  const response = await page.request.post(AUTH_LOGIN_URL, {

    data: { username: user.email, password: user.password },

  });



  if (response.status() === 429) {

    throw new Error(

      'Auth rate limit exceeded (429). Set DEBUG=True (RATE_LIMIT_ENABLED defaults off) or wait before re-running E2E.'

    );

  }

  if (!response.ok()) {

    const body = await response.json().catch(() => ({}));

    throw new Error(`API login failed (${response.status()}): ${JSON.stringify(body)}`);

  }



  const data = (await response.json()) as LoginResponse;

  const orgs = data.organizations ?? [];

  const defaultOrg = orgs.find((m) => m.is_default);

  const membership = defaultOrg ?? orgs[0];

  const orgId = membership?.organization?.id ?? null;



  await page.goto('/login', { waitUntil: 'commit', timeout: 30000 });

  await seedSession(page, data, orgId);



  const authMe = page.waitForResponse(authMeOk, { timeout: 20000 }).catch(() => null);

  await page.goto('/dashboard', { waitUntil: 'commit', timeout: 30000 });

  await authMe;



  await ensureAuthenticated(page);
}



/** Login as user — uses API auth, then lands on dashboard. */

export async function loginAs(page: Page, user: Pick<TestUser, 'email' | 'password'>) {

  await loginViaApi(page, user);

}



function isAppOrigin(url: string): boolean {

  return url.includes('localhost') || url.includes('127.0.0.1');

}



async function clearClientSession(page: Page) {

  if (isAppOrigin(page.url())) {

    await page.evaluate(() => {

      localStorage.clear();

      sessionStorage.clear();

    });

  }

  await page.context().clearCookies();

}



/**

 * Login as user, reusing session when already authenticated as the same account.

 * Use when tests switch between receptionist / doctor / lab tech.

 */

export async function switchUser(page: Page, user: Pick<TestUser, 'email' | 'password'>) {

  let sameUser = false;

  if (isAppOrigin(page.url())) {

    try {

      sameUser = await page.evaluate((email) => {

        const raw = localStorage.getItem('auth_user');

        if (!raw || !localStorage.getItem('auth_tokens')) return false;

        try {

          const u = JSON.parse(raw) as { email?: string; username?: string };

          return u.email === email || u.username === email;

        } catch {

          return false;

        }

      }, user.email);

    } catch {

      sameUser = false;

    }

  }



  if (sameUser) {

    await ensureAuthenticated(page);

    return;

  }



  // Clear session and re-login via API — faster than logout() + full UI round-trip
  await clearClientSession(page);

  try {
    await page.goto('/login', { waitUntil: 'commit', timeout: 15000 });
  } catch {
    // SPA may already be redirecting after session clear
  }

  await loginViaApi(page, user);

}



/**

 * Clear client session (does not call logout API).

 * After clearing tokens, the SPA often redirects to /login itself — a concurrent

 * page.goto then raises net::ERR_ABORTED. Wait for /login instead of forcing goto.

 */

export async function logout(page: Page) {

  await clearClientSession(page);



  if (page.url().includes('/login')) {

    await expect(page.getByLabel('Username or email')).toBeVisible({ timeout: 15000 });

    return;

  }



  try {

    await page.goto('/login', { waitUntil: 'commit', timeout: 15000 });

  } catch {

    // Competing in-app redirect after session clear — acceptable if we land on login

  }



  await page.waitForURL(/\/login/, { timeout: 15000 });

  await expect(page.getByLabel('Username or email')).toBeVisible({ timeout: 15000 });

}



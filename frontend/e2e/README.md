# E2E tests (Playwright)

## Quick start

```bash
# Terminal 1 — backend
cd backend && python manage.py runserver

# Terminal 2 — frontend (or let Playwright start it)
cd frontend && npm start

# Terminal 3 — tests
cd frontend && npm run test:e2e -- e2e/workflows/visit-pay-consult.spec.ts --project=chromium
```

## Prerequisites

- Backend on `http://127.0.0.1:8000`
- Frontend on `http://localhost:3000` (must match `playwright.config.ts` `baseURL` / `webServer.url` host)
- Test users: `python manage.py seed_e2e_users` (auto-run via `e2e/global-setup.ts` when backend is healthy)

## Layout

| Path | Purpose |
|------|---------|
| `helpers/auth.ts` | `loginAs`, `logout`, `gotoAuthenticated` |
| `helpers/test-users.ts` | Credentials aligned with Django seed |
| `helpers/health.ts` | Skip tests when services are down |
| `workflows/` | Cross-role clinical workflows |
| `billing/` | Billing lifecycle specs |

## CI

GitHub Actions job `e2e-tests` in `.github/workflows/ci.yml`:

1. Migrates SQLite + `seed_e2e_users` (users, org membership, `CONS-001`, `CBC-001`)
2. Starts Django on `:8000`
3. Runs Playwright with `CI=true` (starts Vite via `webServer`)

Locally mimic CI:

```bash
cd backend && python manage.py migrate && python manage.py seed_e2e_users
cd backend && python manage.py runserver 127.0.0.1:8000
cd frontend && CI=true npx playwright test --project=chromium
```

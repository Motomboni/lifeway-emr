# Production Readiness Report

This document summarizes the production readiness of the Modern EMR (Django + React + PostgreSQL) and provides a go-live checklist.

---

## Summary

| Area | Status | Notes |
|------|--------|--------|
| **Security hardening** | Done | See [SECURITY_HARDENING.md](./SECURITY_HARDENING.md) |
| **Auth & rate limiting** | Done | Login/refresh/register rate limits; account lockout |
| **Billing / insurance fixes** | Done | Invoice fields, approval defaults, payment-status sync |
| **CI/CD** | Present | Backend tests, frontend lint/test/build, Bandit, npm audit |
| **PWA & offline** | Done | App shell cached via `sw.js`; API network-only; global offline banner |
| **Pre-launch checklist** | Below | Env, CORS, DB SSL, restart backend |

---

## Pre-Launch Checklist

### 1. Environment

- [ ] Copy `.env.prod.example` to `.env` (or your production env store) and set all values.
- [ ] **SECRET_KEY**: Must be a strong random value (≥32 chars). App will not start in production with default or short key.
- [ ] **DEBUG**: Must be `False` in production.
- [ ] **CORS_ALLOWED_ORIGINS**: Set to your frontend origin(s), e.g. `https://emr.yourclinic.com`. If unset, CORS defaults to localhost (see SECURITY_HARDENING.md).
- [ ] **DB_SSLMODE**: For production DB, set to `require` or `verify-full` if your provider supports it.
- [ ] No secrets or API keys committed; use env vars only.

### 2. Backend

- [ ] Restart backend after deploying the latest code so that:
  - Invoice generation uses correct `VisitInsurance` fields (`provider`, `policy_number`).
  - Insurance approval updates `visit.payment_status` and `is_payment_cleared()` treats `INSURANCE_CLAIMED` as cleared.
  - Payment guard middleware can sync `INSURANCE_PENDING` → `SETTLED` for approved insurance.
- [ ] Run migrations: `python manage.py migrate`.
- [ ] Confirm no reliance on `DEBUG=True` for critical behavior.

### 3. Frontend

- [ ] Build with production API URL (e.g. `REACT_APP_*` env at build time) pointing to your production backend.
- [ ] Run `npm run build` and serve the built assets (e.g. via nginx). The PWA service worker (`sw.js`) and `manifest.json` are copied from `public/` and enable install + offline app shell.
- [ ] Serve over HTTPS so the service worker and install prompt work (required for PWA).

### 4. Infrastructure

- [ ] HTTPS only in production (handled by Django settings when `DEBUG=False`).
- [ ] nginx: use `docker/nginx.prod.conf` (or equivalent) with `server_tokens off` and security headers.
- [ ] Database: backups and, if required, SSL as above.

### 5. Optional Cleanups (non-blocking)

- **Backend**: Replace or gate `print()` in `receipt_service.py` and `pdf_service.py` with `logging` (or `if settings.DEBUG: ...`) so production logs stay clean.
- **Frontend**: Remove or gate `console.log` in production builds (e.g. strip in build or use a logger that no-ops in production).

---

## Resolved Issues (for reference)

| Issue | Resolution |
|-------|------------|
| Invoice error: `'VisitInsurance' object has no attribute 'hmo_provider'` | Code uses `insurance.provider` (FK) and `insurance.policy_number`. Restart backend to pick up fix. |
| Insurance approval: "Approved amount must be provided when status is APPROVED" | Serializer defaults `approved_amount` from billing summary when approving; model allows `approved_amount=0`. |
| 403 on consultation: "Payment must be cleared... INSURANCE_PENDING" | Payment guard and `is_payment_cleared()` updated: approve insurance updates `visit.payment_status`; `INSURANCE_CLAIMED` is treated as cleared; middleware syncs old `INSURANCE_PENDING` visits with approved insurance to `SETTLED`. Restart backend. |

---

## CI/CD

- **Backend**: pytest with coverage, migrations on Postgres 15, Codecov upload.
- **Frontend**: lint, tests, production build.
- **Security**: Bandit (Python), `npm audit` (moderate level).

For stricter gates, consider failing CI on Bandit findings or npm audit high/critical (currently `|| true` / `--audit-level=moderate`).

---

## Next Steps (optional)

- Add health-check endpoint (e.g. `/api/health/`) for load balancers and monitoring.
- Configure log aggregation and alerting (e.g. errors, failed logins, audit events).
- Document and test restore from DB backups.
- Consider failing CI on security scan findings once baseline is clean.

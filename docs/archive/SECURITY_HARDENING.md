# Clinic-Grade Security Hardening

This document describes the security measures implemented for the Modern EMR and provides a deployment checklist for clinic-grade (HIPAA-aligned) operation.

## Implemented Controls

### Authentication & Access

| Control | Implementation |
|--------|----------------|
| **JWT with short-lived access tokens** | Access token 15 min; refresh 7 days with rotation |
| **Refresh token rotation & blacklist** | New refresh on use; old token blacklisted on logout |
| **Account lockout** | 5 failed logins → account locked 30 minutes (`User.lock_account`) |
| **Auth endpoint rate limiting** | Login: 5/min, 20/hr per IP; Refresh: 30/min, 200/hr; Register: 3/min, 10/hr |
| **Strong passwords** | Min 12 chars; upper, lower, digit, special; common-password and numeric checks |
| **Production SECRET_KEY enforcement** | App refuses to start if `DEBUG=False` and SECRET_KEY is default or &lt; 32 chars |

### Transport & Headers

| Control | Implementation |
|--------|----------------|
| **HTTPS in production** | `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, HSTS (1 year, includeSubdomains, preload) when not DEBUG |
| **Security headers** | `SecurityHeadersMiddleware`: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy, Permissions-Policy, CSP (configurable) |
| **Cookie hardening** | HttpOnly, SameSite=Lax, Secure in production |
| **CORS** | Explicit `CORS_ALLOWED_ORIGINS` in production; credentials allowed only to those origins |

### Request & Input

| Control | Implementation |
|--------|----------------|
| **Request sanitization** | `RequestSanitizerMiddleware` rejects path traversal (`../`, `..\`, encoded) and null bytes in path/query |
| **Input sanitization** | `core.utils.input_sanitization`: text, phone, email, numeric, date helpers for XSS/injection |
| **CSRF** | Django CSRF middleware; cookie-based for session auth |

### Application & Data

| Control | Implementation |
|--------|----------------|
| **Audit logging** | Append-only `AuditLog`; 7-year retention (configurable); user, role, action, visit, IP, user-agent; no PHI in metadata |
| **RBAC** | Role-based permissions per app; visit-scoped clinical actions |
| **Payment guard** | `PaymentClearedGuard` middleware enforces payment cleared before clinical actions |
| **Database** | PostgreSQL optional SSL via `DB_SSLMODE`; statement timeout 60s for Postgres |

### Infrastructure (Docker / nginx)

| Control | Implementation |
|--------|----------------|
| **nginx** | `server_tokens off`; `client_max_body_size 50m`; X-Frame-Options DENY; Permissions-Policy; proxy timeouts |
| **Secrets** | SECRET_KEY, DB_PASSWORD, API keys via environment (`.env`), not committed |

---

## Deployment Checklist

Before going live:

1. **Secrets**
   - [ ] Set `SECRET_KEY` to a strong random value (`openssl rand -hex 32`).
   - [ ] Set a strong `DB_PASSWORD` and restrict DB network access.
   - [ ] Ensure `.env` is not committed (it is in `.gitignore`).

2. **Environment**
   - [ ] `DEBUG=false`.
   - [ ] `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS` set to your real domain(s) only (no wildcards).

3. **HTTPS**
   - [ ] Terminate TLS at reverse proxy (e.g. Caddy, Traefik, or nginx) and set `X-Forwarded-Proto` and `X-Forwarded-For`.
   - [ ] Redirect HTTP → HTTPS.

4. **Database**
   - [ ] Use PostgreSQL in production (not SQLite).
   - [ ] For clinic-grade: set `DB_SSLMODE=require` (or `verify-full` with CA).

5. **Backups & retention**
   - [ ] Automated backups of DB and media; test restore.
   - [ ] Audit log retention (default 7 years) and backup of audit store.

6. **Users**
   - [ ] Create only necessary accounts; use strong passwords (enforced by validators).
   - [ ] Disable or remove default/test accounts before production.

7. **Monitoring**
   - [ ] Monitor auth failures and lockouts; alert on anomalies.
   - [ ] Review audit logs periodically.

---

## Optional Hardening

- **Redis for rate limiting**  
  Set `REDIS_URL` and switch cache backend to Redis so rate limits and lockout state survive restarts and are shared across workers.

- **Stricter CSP**  
  Adjust `SecurityHeadersMiddleware` CSP to remove `'unsafe-inline'` / `'unsafe-eval'` once all scripts/styles are non-inline and non-eval.

- **IP allowlist for admin**  
  Restrict `/admin/` to trusted IPs at reverse proxy or with Django middleware.

- **MFA**  
  Add two-factor authentication for staff/superuser accounts (e.g. TOTP) for additional clinic-grade assurance.

---

## References

- [Django Security](https://docs.djangoproject.com/en/stable/topics/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/index.html) (high-level alignment: access control, audit, integrity, transmission security)

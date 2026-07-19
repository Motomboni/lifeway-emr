# Security Hardening — Lifeway EMR v2.0

Clinic-grade checklist for production. Referenced by `.env.prod.example`.

## Before go-live

### Secrets

- [ ] `SECRET_KEY` — min 32 chars (`openssl rand -hex 32`)
- [ ] `DB_PASSWORD` — strong, unique
- [ ] Rotate Paystack, Termii, and SMTP credentials from dev values
- [ ] Never commit `.env` to git

### Django

- [ ] `DEBUG=false`
- [ ] `ALLOWED_HOSTS` — production domain only
- [ ] `SECURE_SSL_REDIRECT=true` (or handled at nginx)
- [ ] `SECURE_PROXY_SSL_HEADER=X-Forwarded-Proto` when behind TLS proxy
- [ ] `CORS_ALLOWED_ORIGINS` — explicit frontend origin(s) only

### Authentication

- [ ] JWT access token lifetime 15 min (default)
- [ ] Account lockout after 5 failed attempts (30 min)
- [ ] `RATE_LIMIT_ENABLED=true` in production
- [ ] Redis configured for distributed rate limits (`REDIS_URL`)
- [ ] `PUBLIC_REGISTRATION_ALLOWED_ROLES=PATIENT` (default in production)
- [ ] `API_DOCS_ENABLED=false` unless you need Swagger behind admin auth
- [ ] `HEALTH_DETAILED_PUBLIC=false` (keep `/api/v1/health/` public for load balancers)

### Data & compliance

- [ ] PostgreSQL with encrypted connections (`DB_SSLMODE=require` where supported)
- [ ] Audit logging enabled (`EMR_SETTINGS.ENABLE_AUDIT_LOGGING`)
- [ ] Audit retention aligned with policy (`AUDIT_LOG_RETENTION_DAYS=2555`)
- [ ] Backups tested on schedule

### Patient portal

- [ ] SMTP configured (`EMAIL_BACKEND`, `EMAIL_HOST`, credentials)
- [ ] SMS configured for OTP (`SMS_ENABLED`, Termii or Twilio)
- [ ] OTP email sends in production (not log-only)

### Monitoring

- [ ] Optional `SENTRY_DSN` (backend) and `VITE_SENTRY_DSN` (frontend build)

- [ ] HTTPS everywhere
- [ ] Paystack webhook URL uses HTTPS and signature verification
- [ ] Admin `/admin/` restricted by IP or VPN if possible
- [ ] Media files not publicly listable

## Headers (middleware)

Security headers are applied via `core.middleware.security_headers`. Review CSP if adding third-party scripts.

## Incident response

1. Revoke compromised user passwords / lock accounts in Django admin
2. Rotate `SECRET_KEY` only with planned session invalidation
3. Review audit logs: `/audit-logs`
4. Restore from backup if data integrity affected

## Support

Operations runbook: [docs/OPERATIONS.md](docs/OPERATIONS.md)

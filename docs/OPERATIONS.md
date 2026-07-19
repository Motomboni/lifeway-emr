# Lifeway EMR v2.0 — Operations Runbook

Production deployment for Lifeway Medical Centre. Canonical deploy guide: [docs/DEPLOY.md](./DEPLOY.md).

## Health endpoints

| URL | Purpose |
|-----|---------|
| `GET /api/v1/health/` | Liveness (200 = app running) |
| `GET /api/v1/health/detailed/` | DB + cache checks (503 if unhealthy) |
| `GET /api/v1/health/info/` | Version and environment |

**Docker healthcheck:** `curl -f http://localhost:8000/api/v1/health/`

**Staff UI:** `/health` (Health Status page, admin)

## Required services (production)

| Service | Role |
|---------|------|
| PostgreSQL | Primary database |
| Redis | Celery broker + cache (rate limits) |
| Celery worker | Background tasks |
| Celery beat | Scheduled tasks (audit prune, appointment reminders) |
| Gunicorn/Django | API |
| Nginx | Frontend static + reverse proxy |

Start with: `docker compose -f docker-compose.prod.yml up -d`

## Scheduled tasks (Celery beat)

- **Audit log prune** — weekly; retention from `AUDIT_LOG_RETENTION_DAYS` (default 2555 / 7 years)
- **Appointment reminders** — hourly batch
- **Nightly backup** — 03:00 UTC; copies to `BACKUP_STORAGE_DIR` when set

## Backups

- Manual: superuser → `/backup` UI
- Automated: Celery `apps.backup.tasks.scheduled_backup` (disable with `SCHEDULED_BACKUP_ENABLED=false`)
- Off-site copy: mount volume and set `BACKUP_STORAGE_DIR=/path/to/mount`
- Retention: `BACKUP_RETENTION_DAYS` (default 30)

## Monitoring (optional)

Set `SENTRY_DSN` on backend and `VITE_SENTRY_DSN` on frontend build for error alerting.
See [SECURITY_HARDENING.md](../SECURITY_HARDENING.md).

## Logs

| Location | Content |
|----------|---------|
| `backend/logs/django.log` | Application log |
| `backend/logs/django_errors.log` | Errors only |
| Docker | `docker compose -f docker-compose.prod.yml logs -f backend` |

## Backup & restore

1. **UI:** Superuser → Backup page (`/backup`)
2. **Manual DB:** `pg_dump -U emr_user emr_db > backup.sql`
3. **Restore drill:** restore to staging, run migrations, smoke-test login + patient registration

Set `BACKUP_RETENTION_DAYS` in `.env` (default 30).

## Monitoring checklist

- [ ] Uptime monitor on `/api/v1/health/`
- [ ] Alert on `/api/v1/health/detailed/` 503
- [ ] Disk space on media volume and DB
- [ ] Celery worker running (`docker compose ps`)
- [ ] Paystack webhook delivery (visit payments)
- [ ] SMTP/Termii configured for patient portal OTP

## Environment (Lifeway)

```env
REQUIRE_ORGANIZATION_CONTEXT=false
ENFORCE_PLAN_LIMITS=false
DEBUG=false
CELERY_BROKER_URL=redis://redis:6379/0
REDIS_URL=redis://redis:6379/1
```

## Version

Application version: **2.0.0** — see [CHANGELOG.md](../CHANGELOG.md).

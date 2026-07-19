# Changelog

All notable changes to Lifeway EMR (Modern EMR) are documented here.

## [2.0.0] — 2026-06-25

### Lifeway production baseline

Single-clinic deployment for [Lifeway Medical Centre](https://lmcemr.com.ng). Removed multi-tenant SaaS signup, subscription checkout, and platform billing flows.

### Added

- **IVF module** — cycle management, stimulation monitoring, embryo inventory, sperm analysis
- **Antenatal module** — ANC records, visits, and reporting
- **Deferred payments** — reception billing queue and `/billing/deferred-payments`
- **Paystack visit billing** — reception and patient portal payments with webhook verification
- **Organization backfill** — `backfill_organization` management command for legacy data
- **WeasyPrint PDF export** — receipts and clinical documents (Windows setup documented)
- **Premium auth shell** — branded login with logo, accessibility, and consistent styling
- **Standard API errors** — unified `{ detail, code, fields }` response shape
- **Production Celery stack** — Redis, worker, and beat in `docker-compose.prod.yml`
- **Operations docs** — `docs/OPERATIONS.md` and `SECURITY_HARDENING.md`

### Changed

- **Payment gates** — registration fee required before clinical access; aligned middleware and frontend
- **Plan limits** — `ENFORCE_PLAN_LIMITS=false` by default for Lifeway
- **Audit retention** — prune task respects `AUDIT_LOG_RETENTION_DAYS` (7 years)
- **OTP email** — sends via configured SMTP in production; logs OTP only in DEBUG
- **Redis cache** — enabled when `REDIS_URL` is set (rate limits and health checks)
- **Health checks** — Docker and CI use `/api/v1/health/`
- **Dashboard** — mobile-responsive layout breakpoints
- **Protected routes** — per-route error boundaries via `ProtectedRoute`

### Fixed

- Pending billing queue 500 (`order_by` on related field)
- Patient registration limit false positive (`ENFORCE_PLAN_LIMITS`)
- `NaN` patient ID after registration (API payload normalization)
- Account lockout recovery and failed-login counter reset
- CI YAML env block for E2E jobs

### Removed

- SaaS org signup, subscription APIs, Stripe/Flutterwave SaaS webhooks
- Orphaned subscription plans UI and SaaS alert components

---

## [2.0.1] — 2026-06-25

### Added

- **E2E coverage** — patient portal OTP, lab worklist, pharmacy worklist (Playwright + CI)
- **Scheduled backups** — nightly Celery task with optional `BACKUP_STORAGE_DIR` off-site copy
- **Sentry integration** — optional `SENTRY_DSN` (backend) and `VITE_SENTRY_DSN` (frontend)
- **AuthShell** — register and OTP login aligned with staff login branding
- **E2E OTP helper** — `E2E_OTP_EXPOSE` for CI-only OTP testing (never use in production)

---

## [2.2.0] — 2026-06-25

### Added

- **Scribe → bill** — one-click add validated NHIA tariff items to visit bill from consultation scribe
- **NHIA/HMO claim pack export** — per-visit and batch CSV export (ICD-11, NHIA codes, amounts, patient NHID)
- **Configurable NIN/NHID verification** — `NHID_VERIFICATION_MODE` stub or HTTP provider
- **ANC care schedule** — IPTp, TT, routine visit timeline on antenatal records with WhatsApp reminders
- **NHIA compliance dashboard** — claim readiness, missing NHID, scribe-billed items at `/billing/nhia-compliance`
- **WhatsApp Celery tasks** — 24h/2h appointment reminders and daily ANC reminders
- **Automatic telemedicine transcription** — Whisper runs when a recorded session ends (Celery retries until Twilio media is ready)
- **Live in-call captions** — browser speech recognition during video calls; saved on leave
- **Scribe handoff** — “Use in Clinical Scribe” from completed telemedicine transcripts

---

## [2.1.0] — 2026-06-25

### Added

- **NHIA tariff reference DB** — `NHIATariff` model, admin, and `seed_nhia_tariffs` management command
- **Scribe code validation** — extract and verify `[ICD-11: … / NHIA: …]` pairs against tariff DB on `POST /api/v1/ai/generate-note/`
- **NHIA tariff API** — `GET /api/v1/billing/nhia-tariffs/` (search by ICD-11, NHIA code, or keyword)
- **Consultation scribe panel** — live Clinical AI Scribe on the consultation workspace with one-click apply to form fields and ICD-11 diagnosis codes
- **Note section parser** — maps SOAP / antenatal scribe output to history, examination, diagnosis, and clinical notes

### Changed

- **generate-note** — accepts optional `visit_id`; response includes `code_validation`, `parsed_sections`, and `icd11_apply_payload`

---

## [1.x] — prior releases

Visit-scoped EMR core: patients, visits, consultation, lab, radiology, pharmacy, billing, audit logs, patient portal, telemedicine, appointments, and reports.

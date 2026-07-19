# Lifeway EMR – Deploy with Docker

## Push to GitHub

1. **Create a repo** (if needed): [GitHub New Repository](https://github.com/new). Do not initialize with README if you already have a local repo.

2. **Add remote and push** (from project root):

   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git branch -M main
   git push -u origin main
   ```

3. **Secrets**: Never commit `.env` or real `SECRET_KEY`/passwords. Use GitHub Secrets for CI (e.g. `DOCKER_HUB_TOKEN`, `DB_PASSWORD`) if you use Actions.

---

## Deploy with Docker

### 1. Prepare environment

```bash
cp .env.prod.example .env
# Edit .env: set SECRET_KEY (e.g. openssl rand -hex 32) and DB_PASSWORD
```

Required in `.env` for production:

- `SECRET_KEY` – long random value (min 32 chars)
- `DB_PASSWORD` – Postgres password (required by prod compose)
- `ALLOWED_HOSTS` – include your public hostname(s)
- `CORS_ALLOWED_ORIGINS` – include your frontend URL(s)
- `FRONTEND_URL` – public SPA URL used in links/callbacks
- `SECURE_SSL_REDIRECT` / `SECURE_PROXY_SSL_HEADER` – match your HTTPS/reverse-proxy setup

Optional one-time admin bootstrap:

```bash
export DJANGO_SUPERUSER_USERNAME=admin
export DJANGO_SUPERUSER_EMAIL=admin@yourdomain.com
export DJANGO_SUPERUSER_ROLE=ADMIN
export DJANGO_SUPERUSER_PASSWORD='use-a-strong-temporary-password'
python backend/create_superuser.py
unset DJANGO_SUPERUSER_PASSWORD
```

The script is idempotent: if the username already exists, it exits without changing the account.

Do not put real admin passwords, API tokens, or database passwords into source-controlled files.

### 2. Option A – Multi-service (recommended for production)

Separate backend, frontend, and database. Frontend nginx proxies `/api/`, `/static/`, `/media/` to the backend.

```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

- App: **http://localhost:80** (or your server IP/domain)
- Backend health: service `backend` on port 8000 (internal)
- Persistence: `postgres_data`, `media_data` volumes

### 3a. Radiology imaging stack (Orthanc + MinIO + OHIF)

Add DICOMweb storage and an in-browser OHIF viewer alongside the main compose file:

```bash
docker compose -f docker-compose.standalone.yml -f docker-compose.imaging.yml -f docker-compose.imaging.env.yml up -d
# or multi-service:
docker compose -f docker-compose.prod.yml -f docker-compose.imaging.yml -f docker-compose.imaging.env.yml up -d
```

Set in `.env` (see `.env.prod.example`):

- `ORTHANC_URL=http://orthanc:8042`
- `ORTHANC_USERNAME` / `ORTHANC_PASSWORD` — match `docker/orthanc/orthanc.json`
- `OHIF_VIEWER_URL=/ohif/viewer` — same-origin path proxied by nginx to Orthanc
- `AWS_S3_ENDPOINT_URL=http://minio:9000` — optional MinIO backing for PACS-lite files

After upload from **Radiology Orders → DICOM Imaging**, open **Open Viewer** to load the study in OHIF.

Local dev (Orthanc on port 8042):

```bash
docker compose -f docker-compose.imaging.yml up -d
cd backend && ORTHANC_URL=http://127.0.0.1:8042 OHIF_VIEWER_URL=/ohif/viewer python manage.py runserver
cd frontend && npm run dev
```

Vite proxies `/ohif` and `/orthanc` to Orthanc with basic auth.

### 3. Option B – Single-container (all-in-one)

One app image (nginx + Gunicorn) plus Postgres. Good for simple VPS or single-node deploy.

```bash
docker compose -f docker-compose.standalone.yml build
docker compose -f docker-compose.standalone.yml up -d
```

For DICOM/OHIF (`/ohif/`, `/orthanc/` nginx routes), also merge the imaging stack:

```bash
docker compose -f docker-compose.standalone.yml -f docker-compose.imaging.yml -f docker-compose.imaging.env.yml up -d
```

Without the imaging overlay, radiology uploads still work (PACS-lite + optional Orthanc STOW via `ORTHANC_URL`), but in-container nginx will not proxy OHIF until Orthanc is on the compose network.

- App: **http://localhost:80**
- Persistence: `postgres_data`, `media_data` volumes

### 4. Build images only (e.g. for a registry)

```bash
# Multi-service
docker compose -f docker-compose.prod.yml build
# Tag and push to your registry as needed:
# docker tag emr-backend:latest your-registry/emr-backend:latest
# docker push your-registry/emr-backend:latest

# Single-container
docker build -t emr-app:latest .
# docker tag emr-app:latest your-registry/emr-app:latest
# docker push your-registry/emr-app:latest
```

---

## Compose files summary

| File | Use case |
|------|----------|
| `docker-compose.yml` | Local dev: backend (runserver) + frontend (built) + db |
| `docker-compose.prod.yml` | Production: backend (Gunicorn) + frontend (nginx) + db |
| `docker-compose.standalone.yml` | Production: one app container (root Dockerfile) + db |
| `docker-compose.imaging.yml` | Orthanc + MinIO imaging stack (merge with prod/standalone) |
| `docker-compose.imaging.env.yml` | EMR app env for Orthanc/MinIO (merge with imaging stack) |

---

## Health and logs

- **Backend**: `curl http://localhost:8000/api/v1/` (multi-service) or use frontend `/health` (standalone).
- **Logs**: `docker compose -f docker-compose.prod.yml logs -f backend`
- **Restart**: `docker compose -f docker-compose.prod.yml restart backend`

---

## Final staging smoke test

Run these before a production cutover:

```bash
python backend/manage.py check --deploy
python backend/manage.py collectstatic --noinput
npm run build --prefix frontend
```

Then confirm these user flows against the staging URL:

- Login as an admin/doctor user.
- Open `/visits` and confirm pagination shows the migrated total, not just the first page.
- Open a migrated patient and a migrated visit.
- Open visit billing, lab, prescription, and radiology panels.
- Generate a receipt/invoice if PDF features are in scope.
- **Telemedicine:** create session (with recording consent), confirm Termii SMS invite, join `/telemedicine/room/{id}`.
- **NHIA:** open visit NHIA claim panel — validate, download claim pack CSV, upload manually via the official NHIA portal (no public API), then record submitted/paid/denied in the EMR.
- Verify `tmp/lmc_migration/reconciliation.csv` or the archived migration report has business sign-off.

### Quick server deploy (lmcemr.com.ng)

On the production VPS after pushing to `main`:

```bash
cd ~/lifeway-emr
bash scripts/deploy-lifeway-production.sh
```

Required production env for telemedicine + NHIA workflows:

| Variable | Purpose |
|----------|---------|
| `FRONTEND_URL` | Meeting links in SMS (`/telemedicine/room/{id}`) |
| `SMS_ENABLED` + `TERMII_*` | Patient telemedicine invites |
| `TWILIO_*` | Video rooms and recording |
| `OPENAI_API_KEY` | Post-call transcription (optional) |


Known deployment dependencies:

- Install WeasyPrint native libraries on the server if PDF output is required.
- Enforce HTTPS either at Django (`SECURE_SSL_REDIRECT=true`) or at the reverse proxy/load balancer.
- Rotate any local credentials that were ever exposed during setup.

---

## Optional: GitHub Actions (build and push images)

Example job to build and push on push to `main` (add to `.github/workflows/docker.yml`):

```yaml
name: Docker build
on:
  push:
    branches: [main]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - name: Build prod images
        run: |
          docker compose -f docker-compose.prod.yml build
      # Add push to Docker Hub / GHCR using secrets (DOCKER_HUB_USERNAME, DOCKER_HUB_TOKEN, etc.)
```

After pushing to GitHub, deploy on your server by pulling the images and running the chosen compose file with your `.env`.

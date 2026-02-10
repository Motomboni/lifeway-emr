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

### 2. Option A – Multi-service (recommended for production)

Separate backend, frontend, and database. Frontend nginx proxies `/api/`, `/static/`, `/media/` to the backend.

```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

- App: **http://localhost:80** (or your server IP/domain)
- Backend health: service `backend` on port 8000 (internal)
- Persistence: `postgres_data`, `media_data` volumes

### 3. Option B – Single-container (all-in-one)

One app image (nginx + Gunicorn) plus Postgres. Good for simple VPS or single-node deploy.

```bash
docker compose -f docker-compose.standalone.yml build
docker compose -f docker-compose.standalone.yml up -d
```

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

---

## Health and logs

- **Backend**: `curl http://localhost:8000/api/v1/` (multi-service) or use frontend `/health` (standalone).
- **Logs**: `docker compose -f docker-compose.prod.yml logs -f backend`
- **Restart**: `docker compose -f docker-compose.prod.yml restart backend`

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

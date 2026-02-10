# Production Docker Setup (Django + React + Postgres)

This project includes a production-ready Docker setup with:

- **PostgreSQL 15** – database
- **Django (Gunicorn)** – API and admin; serves `/api/`, `/static/`, `/media/`
- **React (nginx)** – SPA on port 80; proxies API/static/media to Django

## Prerequisites

- Docker Engine 20.10+
- Docker Compose v2

## Quick start

1. **Create environment file**

   ```bash
   cp .env.prod.example .env
   ```

   Edit `.env` and set at least:

   - `SECRET_KEY` (e.g. `openssl rand -hex 32`)
   - `DB_PASSWORD` (strong password for Postgres)
   - `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS` for your domain(s)

2. **Build and run**

   ```bash
   docker compose -f docker-compose.prod.yml build
   docker compose -f docker-compose.prod.yml up -d
   ```

3. **Open the app**

   - App (React): http://localhost  
   - API: http://localhost/api/v1/  
   - Admin: http://localhost/admin/ (create superuser first)

4. **Create a superuser (one-off)**

   ```bash
   docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
   ```

## Compose commands

| Command | Description |
|--------|-------------|
| `docker compose -f docker-compose.prod.yml up -d` | Start all services in background |
| `docker compose -f docker-compose.prod.yml down` | Stop and remove containers |
| `docker compose -f docker-compose.prod.yml logs -f backend` | Follow backend logs |
| `docker compose -f docker-compose.prod.yml exec backend python manage.py shell` | Django shell |
| `docker compose -f docker-compose.prod.yml exec db psql -U emr_user -d emr_db` | Postgres shell |

## Architecture

- **db** – Postgres 15 Alpine; data in volume `postgres_data`.
- **backend** – Django app running Gunicorn. On start, entrypoint waits for DB, runs `migrate` and `collectstatic`, then starts Gunicorn. Media files are stored in volume `media_data`.
- **frontend** – React build served by nginx. Proxies `/api/`, `/static/`, `/media/` to `backend:8000`; everything else is the SPA.

Build context for both images is the **repository root** so that `backend/Dockerfile` and `frontend/Dockerfile` can reference `backend/`, `frontend/`, and `docker/` correctly.

## Files

| File | Purpose |
|------|--------|
| `docker-compose.prod.yml` | Production stack (db, backend, frontend) |
| `backend/Dockerfile` | Multi-stage: build deps → runtime + Gunicorn |
| `frontend/Dockerfile` | Multi-stage: Node build → nginx serving build |
| `docker/nginx.prod.conf` | nginx config (proxy + SPA) |
| `docker/entrypoint-backend.sh` | Backend entrypoint (wait DB, migrate, collectstatic, gosu → Gunicorn) |
| `.env.prod.example` | Example env for production; copy to `.env` |

## Environment variables

See `.env.prod.example`. Required for production:

- `SECRET_KEY` – Django secret
- `DB_PASSWORD` – Postgres password (must match `POSTGRES_PASSWORD` in compose; compose passes it from `.env`)
- `ALLOWED_HOSTS` – Comma-separated hosts (include `localhost`, `backend`, and your public domain)
- `CORS_ALLOWED_ORIGINS` – Comma-separated origins for the frontend (e.g. `https://yourdomain.com`)

## HTTPS / reverse proxy

For HTTPS, run a reverse proxy (e.g. Traefik, Caddy, or nginx) on the host and proxy to `frontend:80`. Set `X-Forwarded-Proto` and `X-Forwarded-For` so Django and CORS behave correctly. Alternatively, add an nginx service in front that terminates TLS and proxies to the `frontend` service.

## Development vs production

- **Development**: use the existing `docker-compose.yml` (e.g. `runserver`, hot reload).  
- **Production**: use `docker-compose.prod.yml` (Gunicorn, built React, no code mounts).

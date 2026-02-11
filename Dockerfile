# Multi-stage Dockerfile for EMR System (single-container: nginx + gunicorn)
# Build from repo root: docker build -t emr-app .
# Run with a separate db service; set DB_HOST to the db service name.

# Stage 1: Backend
FROM python:3.11-slim AS backend

WORKDIR /app/backend

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt gunicorn

COPY backend/ .
RUN python manage.py collectstatic --noinput || true

# Stage 2: Frontend
FROM node:22-alpine AS frontend

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --omit=dev

COPY frontend/ .
ENV CI=true
ENV GENERATE_SOURCEMAP=false
RUN npm run build

# Stage 3: Production (all-in-one)
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps from backend stage (no code yet, for path layout)
COPY --from=backend /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend /usr/local/bin /usr/local/bin
COPY --from=backend /app/backend /app/backend

COPY --from=frontend /app/frontend/build /app/frontend/build

# Nginx: proxy to 127.0.0.1:8000 (same container)
COPY docker/nginx.standalone.conf /etc/nginx/sites-available/default
RUN ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/ 2>/dev/null || true

COPY docker/start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 80

CMD ["/start.sh"]

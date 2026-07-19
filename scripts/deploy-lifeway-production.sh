#!/usr/bin/env bash
# Lifeway EMR production deploy (standalone single-container + Postgres).
# Run on the server from repo root after git pull.
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.standalone.yml}"

echo "==> Lifeway EMR deploy ($(date -u +%Y-%m-%dT%H:%M:%SZ))"

if [[ ! -f .env ]]; then
  echo "Missing .env — copy .env.prod.example and set SECRET_KEY, DB_PASSWORD, FRONTEND_URL, Termii/Twilio keys."
  exit 1
fi

echo "==> Pull latest code"
git pull origin main

echo "==> Rebuild and restart"
docker compose -f "$COMPOSE_FILE" up -d --build --force-recreate --remove-orphans

echo "==> Wait for healthy app"
sleep 15
docker compose -f "$COMPOSE_FILE" ps

echo "==> Migrate database"
docker compose -f "$COMPOSE_FILE" exec -T app python /app/backend/manage.py migrate --noinput

echo "==> Seed reference data (NHIA tariffs + medication interactions)"
docker compose -f "$COMPOSE_FILE" exec -T app python /app/backend/manage.py seed_nhia_tariffs
docker compose -f "$COMPOSE_FILE" exec -T app python /app/backend/manage.py seed_medication_interactions

echo "==> Collect static"
docker compose -f "$COMPOSE_FILE" exec -T app python /app/backend/manage.py collectstatic --noinput

echo "==> Deploy checks"
docker compose -f "$COMPOSE_FILE" exec -T app python /app/backend/manage.py check --deploy

echo ""
echo "Smoke test (manual):"
echo "  1. Login at FRONTEND_URL"
echo "  2. Open a visit — billing gates, NHIA claim panel, telemedicine button"
echo "  3. Create telemedicine session — patient SMS invite (Termii)"
echo "  4. Join /telemedicine/room/{sessionId} as doctor and patient"
echo "  5. NHIA Compliance dashboard — validate/export a claim"
echo ""
echo "Deploy complete."

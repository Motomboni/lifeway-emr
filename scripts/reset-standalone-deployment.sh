#!/usr/bin/env bash
# Reset Postgres volume and redeploy standalone stack (DESTROYS ALL DB DATA).
# Usage (repo root): bash scripts/reset-standalone-deployment.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "This will remove volume postgres_data and rebuild the app image."
echo "ALL DATABASE DATA FOR THIS COMPOSE PROJECT WILL BE LOST."
read -r -p "Type YES to continue: " confirm
if [[ "$confirm" != "YES" ]]; then echo "Aborted."; exit 1; fi

docker compose -f docker-compose.standalone.yml down -v --remove-orphans
docker compose -f docker-compose.standalone.yml build --no-cache app
docker compose -f docker-compose.standalone.yml up -d

echo "Done. App: http://localhost:8080 — migrations run automatically via docker/start.sh."

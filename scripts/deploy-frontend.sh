#!/bin/bash
# Deploy frontend updates to the remote server.
# Run this ON THE REMOTE SERVER after you've pushed from your local machine.
#
# Usage: cd ~/lifeway-emr && bash scripts/deploy-frontend.sh
#
# If you use the STANDALONE setup (single app container), run with:
#   bash scripts/deploy-frontend.sh standalone
#
# If you use the default docker-compose (separate frontend/backend), run with:
#   bash scripts/deploy-frontend.sh
#   (or: bash scripts/deploy-frontend.sh default)

set -e
MODE="${1:-default}"

echo "=== Fetching latest from GitHub ==="
git fetch origin
git reset --hard origin/main

echo ""
if [ "$MODE" = "standalone" ]; then
  echo "=== Rebuilding STANDALONE app (all-in-one container) ==="
  echo "Using: docker-compose.standalone.yml"
  docker compose -f docker-compose.standalone.yml build --no-cache app
  docker compose -f docker-compose.standalone.yml up -d
  echo ""
  echo "=== Done. App should be at http://YOUR-SERVER:8080 ==="
else
  echo "=== Rebuilding frontend (default docker-compose) ==="
  docker compose build --no-cache frontend
  docker compose up -d
  echo ""
  echo "=== Done. Frontend should be at http://YOUR-SERVER:3000 ==="
fi

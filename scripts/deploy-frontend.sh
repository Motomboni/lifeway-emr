#!/bin/bash
# Deploy frontend updates to the remote server.
# Run this ON THE REMOTE SERVER after you've pushed from your local machine.
# Usage: cd ~/lifeway-emr && bash scripts/deploy-frontend.sh

set -e
echo "=== Fetching latest from GitHub ==="
git fetch origin
git reset --hard origin/main

echo ""
echo "=== Rebuilding frontend (no cache) ==="
docker compose build --no-cache frontend

echo ""
echo "=== Restarting containers ==="
docker compose up -d

echo ""
echo "=== Done. Frontend should be live at http://$(hostname -I | awk '{print $1}'):3000 ==="

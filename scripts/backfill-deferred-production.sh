#!/usr/bin/env bash
# Backfill deferred legacy VisitCharges on a production standalone host.
# Prereqs: tmp/lifeway_csv/*.csv on the server (from migrate_lifeway/restore_export.py).
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -d tmp/lifeway_csv ]] || [[ ! -f tmp/lifeway_csv/tblPatientPayment.csv ]]; then
  echo "Missing tmp/lifeway_csv/tblPatientPayment.csv"
  echo "Copy LIFEWAY exports to tmp/lifeway_csv/ first."
  exit 1
fi

echo "Recreating app with tmp/docs mounts..."
docker compose -f docker-compose.standalone.yml up -d --force-recreate app

echo "Dry run..."
docker compose -f docker-compose.standalone.yml exec app \
  python /app/backend/manage.py backfill_legacy_migration --dry-run

read -r -p "Run backfill for real? [y/N] " confirm
if [[ "${confirm,,}" != "y" ]]; then
  echo "Aborted."
  exit 0
fi

docker compose -f docker-compose.standalone.yml exec app \
  python /app/backend/manage.py backfill_legacy_migration

echo "Deferred charge count:"
docker compose -f docker-compose.standalone.yml exec app \
  python /app/backend/manage.py shell -c \
  "from apps.billing.models import VisitCharge; print(VisitCharge.objects.filter(description__startswith='[Legacy Deferred PatientPayID:').count())"

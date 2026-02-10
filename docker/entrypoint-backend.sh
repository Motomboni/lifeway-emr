#!/bin/sh
set -e

echo "Waiting for database..."
while ! python -c "
import os
import sys
import socket
host = os.environ.get('DB_HOST', 'db')
port = int(os.environ.get('DB_PORT', '5432'))
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.settimeout(2)
    s.connect((host, port))
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
    sleep 2
done
echo "Database is ready."

cd /app

# Ensure app user can write to mounted volumes
chown -R app:app /app/staticfiles /app/media 2>/dev/null || true

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Run CMD as app user (e.g. gunicorn)
exec gosu app "$@"

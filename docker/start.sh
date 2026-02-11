#!/bin/bash
set -e

# Wait for database (no netcat required)
echo "Waiting for database..."
host="${DB_HOST:-db}"
port="${DB_PORT:-5432}"
attempt=0
max_attempts=60
until python3 -c "
import socket, sys
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.settimeout(3)
    s.connect(('$host', int('$port')))
    s.close()
    sys.exit(0)
except Exception as e:
    sys.exit(1)
"; do
  attempt=$((attempt + 1))
  echo "  Attempt $attempt/$max_attempts: $host:$port unreachable, retrying in 2s..."
  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "ERROR: Database at $host:$port did not become ready in time."
    exit 1
  fi
  sleep 2
done
echo "Database is ready!"

# Run migrations
cd /app/backend
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput

# Start nginx in background
nginx -g "daemon off;" &  # run in shell background so gunicorn can start

# Start Django with Gunicorn (production WSGI server)
gunicorn core.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info

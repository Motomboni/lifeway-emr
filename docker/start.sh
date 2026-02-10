#!/bin/bash
set -e

# Wait for database (no netcat required)
echo "Waiting for database..."
until python -c "
import os, socket, sys
host = os.environ.get('DB_HOST', 'db')
port = int(os.environ.get('DB_PORT', '5432'))
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.settimeout(2)
    s.connect((host, port))
    s.close()
except Exception:
    sys.exit(1)
" 2>/dev/null; do
  sleep 2
done
echo "Database is ready!"

# Run migrations
cd /app/backend
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput

# Start nginx in background
nginx

# Start Django with Gunicorn (production WSGI server)
gunicorn core.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info

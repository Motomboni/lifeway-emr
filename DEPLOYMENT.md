# Deployment Guide

## Overview

This guide covers deploying the Modern EMR system to production.

## Prerequisites

- Docker and Docker Compose installed
- Domain name with SSL certificate
- PostgreSQL database (or use Docker Compose)
- Redis (for caching and rate limiting)
- SMTP server for email notifications

## Environment Setup

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Update `.env` with production values:
- Set `DEBUG=False`
- Generate a strong `SECRET_KEY`
- Configure database credentials
- Set up Redis URL
- Configure email settings
- Set `ALLOWED_HOSTS` to your domain

## Docker Deployment

### Build and Run

```bash
# Build images
docker-compose build

# Run migrations
docker-compose run backend python manage.py migrate

# Create superuser
docker-compose run backend python manage.py createsuperuser

# Start services
docker-compose up -d
```

### Production with Gunicorn

Update `docker-compose.yml` backend service command:
```yaml
command: gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

## Manual Deployment

### Backend

1. Install dependencies:
```bash
cd backend
pip install -r requirements.txt
```

2. Run migrations:
```bash
python manage.py migrate
```

3. Collect static files:
```bash
python manage.py collectstatic --noinput
```

4. Start with Gunicorn:
```bash
gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

### Frontend

1. Build for production:
```bash
cd frontend
npm install
npm run build
```

2. Serve with Nginx:
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    root /path/to/frontend/build;
    index index.html;
    
    location /api/ {
        proxy_pass http://localhost:8000;
    }
    
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

## SSL/HTTPS Setup

Use Let's Encrypt with Certbot:

```bash
certbot --nginx -d yourdomain.com
```

Update Django settings:
- `SECURE_SSL_REDIRECT = True`
- `SESSION_COOKIE_SECURE = True`
- `CSRF_COOKIE_SECURE = True`

## Monitoring

### Health Checks

- Backend: `http://yourdomain.com/api/v1/`
- Frontend: `http://yourdomain.com/`

### Logging

Logs are written to:
- Django: `/var/log/emr/django.log`
- Nginx: `/var/log/nginx/access.log` and `/var/log/nginx/error.log`

## Backup Strategy

1. Database backups (daily):
```bash
pg_dump -U emr_user emr_db > backup_$(date +%Y%m%d).sql
```

2. Static files backup
3. Audit logs retention (7 years for HIPAA compliance)

## Scaling

### Horizontal Scaling

- Use load balancer (Nginx, HAProxy)
- Multiple Gunicorn workers
- Database connection pooling
- Redis for session storage

### Vertical Scaling

- Increase server resources
- Optimize database queries
- Enable caching

## Security Checklist

- [ ] `DEBUG=False` in production
- [ ] Strong `SECRET_KEY`
- [ ] SSL/HTTPS enabled
- [ ] Security headers configured
- [ ] Rate limiting enabled
- [ ] Database credentials secured
- [ ] Regular security updates
- [ ] Firewall configured
- [ ] Audit logs enabled
- [ ] Backup strategy in place

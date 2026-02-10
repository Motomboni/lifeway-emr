# Environment Configuration Guide

## Overview

The EMR system uses environment variables for configuration. This guide explains how to set up your `.env` file.

## Quick Start

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your configuration values

3. The Django backend will automatically load these variables

## Configuration Sections

### 1. Django Settings

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

- **SECRET_KEY**: Generate a random string for production
- **DEBUG**: Set to `False` in production
- **ALLOWED_HOSTS**: Comma-separated list of allowed hostnames

### 2. Database Configuration

**SQLite (Development - Default):**
```env
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
```

**PostgreSQL (Production):**
```env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=emr_db
DB_USER=emr_user
DB_PASSWORD=emr_password
DB_HOST=localhost
DB_PORT=5432
```

### 3. Email Configuration

**Development (Console - emails print to console):**
```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

**Production (SMTP):**
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@emr.example.com
```

### 4. SMS Configuration

**Development (Console - SMS logs to console):**
```env
SMS_ENABLED=True
SMS_PROVIDER=console
```

**Production (Twilio):**
```env
SMS_ENABLED=True
SMS_PROVIDER=twilio
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1234567890
```

### 5. Twilio Video (Telemedicine)

```env
TWILIO_API_KEY=your-api-key-sid
TWILIO_API_SECRET=your-api-secret
TWILIO_RECORDING_ENABLED=False
```

**To get Twilio credentials:**
1. Sign up at https://www.twilio.com/
2. Get Account SID and Auth Token from Console
3. Create API Key for Video (Account → API Keys & Tokens)
4. Save API Key SID and Secret

### 6. Backup Configuration

```env
BACKUP_RETENTION_DAYS=30
```

### 7. Redis (Optional)

```env
REDIS_URL=redis://localhost:6379/1
```

## Production Checklist

Before deploying to production:

- [ ] Change `SECRET_KEY` to a random string
- [ ] Set `DEBUG=False`
- [ ] Configure `ALLOWED_HOSTS` with your domain
- [ ] Set up PostgreSQL database
- [ ] Configure SMTP email settings
- [ ] Set up Twilio credentials (if using SMS/Video)
- [ ] Enable HTTPS and set security flags:
  - `SESSION_COOKIE_SECURE=True`
  - `CSRF_COOKIE_SECURE=True`
  - `SECURE_SSL_REDIRECT=True`

## Security Notes

- **Never commit `.env` to version control**
- `.env` is already in `.gitignore`
- Use strong passwords for production
- Rotate secrets regularly
- Use environment-specific `.env` files

## Loading Environment Variables

The Django settings file automatically loads from `.env` using `os.environ.get()`.

For production, you can also:
- Use system environment variables
- Use a secrets management service
- Use Docker environment variables

## Example Production .env

```env
SECRET_KEY=your-very-long-random-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

DB_ENGINE=django.db.backends.postgresql
DB_NAME=emr_production
DB_USER=emr_user
DB_PASSWORD=strong-password-here
DB_HOST=db.yourdomain.com
DB_PORT=5432

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@yourdomain.com
EMAIL_HOST_PASSWORD=app-specific-password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

SMS_ENABLED=True
SMS_PROVIDER=twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1234567890

TWILIO_API_KEY=SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_API_SECRET=your-api-secret
TWILIO_RECORDING_ENABLED=True

SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
```

## Troubleshooting

### Variables not loading
- Ensure `.env` file is in the project root
- Check for typos in variable names
- Restart the Django server after changes

### Database connection errors
- Verify database credentials
- Ensure database server is running
- Check network connectivity

### Email not sending
- Verify SMTP credentials
- Check firewall settings
- For Gmail, use App Password (not regular password)

### Twilio errors
- Verify all credentials are correct
- Check Twilio account status
- Ensure sufficient account balance

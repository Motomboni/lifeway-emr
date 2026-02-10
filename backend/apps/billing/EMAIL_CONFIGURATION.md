# Email Configuration for Invoice/Receipt Sending

## Overview

The system can send invoices and receipts via email with PDF attachments. Email configuration is required in Django settings.

## Django Settings

Add to `backend/core/settings.py`:

```python
# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # Or your SMTP server
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'  # Use app password for Gmail
DEFAULT_FROM_EMAIL = 'your-email@gmail.com'
```

## Gmail Setup

1. Enable 2-Factor Authentication
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Use the app password in `EMAIL_HOST_PASSWORD`

## Other Email Providers

### SendGrid
```python
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'apikey'
EMAIL_HOST_PASSWORD = 'your-sendgrid-api-key'
```

### AWS SES
```python
EMAIL_BACKEND = 'django_ses.SESBackend'
AWS_SES_REGION_NAME = 'us-east-1'
AWS_SES_REGION_ENDPOINT = 'email.us-east-1.amazonaws.com'
```

### Mailgun
```python
EMAIL_HOST = 'smtp.mailgun.org'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'postmaster@your-domain.mailgun.org'
EMAIL_HOST_PASSWORD = 'your-mailgun-password'
```

## Testing Email

```python
# In Django shell
from django.core.mail import send_mail
send_mail(
    'Test Subject',
    'Test message',
    'from@example.com',
    ['to@example.com'],
    fail_silently=False,
)
```

## Email Service Features

- ✅ Sends receipt/invoice as email
- ✅ Attaches PDF if available
- ✅ Professional email templates
- ✅ Tracks email delivery in database
- ✅ Audit logging for compliance

## API Endpoints

- `POST /api/v1/visits/{visit_id}/billing/receipt/send-email/`
  - Body: `{ "email": "patient@example.com" }`
  
- `POST /api/v1/visits/{visit_id}/billing/invoice/send-email/`
  - Body: `{ "email": "patient@example.com" }`

## Notes

- Email sending is logged in `InvoiceReceipt` model
- PDF attachment is included if PDF generation is available
- Email sending failures are logged but don't break the flow
- Receptionist role required to send emails


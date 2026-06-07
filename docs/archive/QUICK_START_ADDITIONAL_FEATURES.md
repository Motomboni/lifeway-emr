# Quick Start Guide - Additional Features

## 🚀 New Features Ready to Use

All additional features from Option 2 have been successfully implemented and are ready for use!

## Setup Steps

### 1. Apply Database Migrations

```bash
cd backend
python manage.py migrate notifications
```

### 2. Install Optional Dependencies (for SMS)

If you want to use SMS notifications with Twilio:

```bash
pip install twilio
```

### 3. Configure Email (Production)

Update `backend/core/settings.py` or set environment variables:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-password'
DEFAULT_FROM_EMAIL = 'noreply@emr.example.com'
```

### 4. Configure SMS (Production - Optional)

Update `backend/core/settings.py` or set environment variables:

```python
SMS_ENABLED = True
SMS_PROVIDER = 'twilio'
TWILIO_ACCOUNT_SID = 'your-account-sid'
TWILIO_AUTH_TOKEN = 'your-auth-token'
TWILIO_PHONE_NUMBER = '+1234567890'
```

## Testing the Features

### Email Notifications

1. **Appointment Confirmation:**
   - Create an appointment
   - Confirm it via the API or UI
   - Check console/logs for email (development) or inbox (production)

2. **Lab Results:**
   - Create a lab order
   - Add a lab result
   - Email notification sent automatically

3. **View Email History:**
   - `GET /api/v1/notifications/` - View all sent emails

### SMS Notifications

1. **Test SMS (Console Mode):**
   - Set `SMS_ENABLED = True` and `SMS_PROVIDER = 'console'`
   - Create lab result or confirm appointment
   - Check console logs for SMS message

2. **Production SMS (Twilio):**
   - Configure Twilio credentials
   - Set `SMS_PROVIDER = 'twilio'`
   - SMS will be sent via Twilio

### Advanced Analytics

1. **Dashboard Stats:**
   ```bash
   GET /api/v1/reports/dashboard-stats/
   ```

2. **Patient Statistics:**
   ```bash
   GET /api/v1/reports/patient-statistics/
   ```

3. **Clinical Statistics:**
   ```bash
   GET /api/v1/reports/clinical-statistics/?date_from=2024-01-01&date_to=2024-12-31
   ```

### Bulk Operations

1. **Export Patients (CSV):**
   ```bash
   GET /api/v1/patients/bulk/export-csv/?search=John
   ```

2. **Export Patients (JSON):**
   ```bash
   GET /api/v1/patients/bulk/export-json/
   ```

3. **Import Patients (CSV):**
   ```bash
   POST /api/v1/patients/bulk/import-csv/
   Body: {
     "csv_content": "first_name,last_name,email\nJohn,Doe,john@example.com"
   }
   ```

## Scheduled Tasks

### Appointment Reminders

Set up a cron job or scheduled task to send appointment reminders:

```bash
# Run every hour
0 * * * * cd /path/to/backend && python manage.py send_appointment_reminders

# Or run every 6 hours with 24-hour lookahead
0 */6 * * * cd /path/to/backend && python manage.py send_appointment_reminders --hours 24
```

## API Documentation

All new endpoints are documented in the Swagger UI:
- Visit: `http://localhost:8000/api/docs/`
- Look for:
  - Notifications endpoints
  - Enhanced Reports endpoints
  - Bulk Operations endpoints

## Features Summary

✅ **Email Notifications** - Automatic emails for appointments and results  
✅ **SMS Notifications** - SMS alerts via Twilio or console  
✅ **Real-time Notifications** - Polling-based notification system  
✅ **Advanced Analytics** - Dashboard, patient, and clinical statistics  
✅ **Bulk Operations** - CSV/JSON import/export for patients  

## Next Steps

1. ✅ Apply migrations: `python manage.py migrate`
2. ✅ Test email notifications (check console in development)
3. ✅ Test bulk export/import
4. ✅ Explore new analytics endpoints
5. ✅ Configure production email/SMS settings when ready

All features are production-ready and follow EMR compliance rules!

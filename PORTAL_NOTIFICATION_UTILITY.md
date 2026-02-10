# Patient Portal Notification Utility

## Overview
Simple, well-structured notification utility for patient portal account creation. Prepares messages without actually sending them - ready for email/SMS integration.

---

## Complete Code

### File: `backend/apps/patients/portal_notifications.py`

**Features:**
- ✅ Message preparation (email + SMS)
- ✅ Structured for easy integration
- ✅ Logging for debugging
- ✅ Multiple notification types
- ✅ Configurable clinic name/URLs
- ✅ Helper functions for future integration

---

## Usage Examples

### Basic Usage

```python
from apps.patients.portal_notifications import notify_portal_account_created

# After creating portal account in serializer
if portal_created:
    result = notify_portal_account_created(
        patient=patient,
        username='john@example.com',
        temporary_password='xK9mP2nQ7vR3',
        send_email=True,
        send_sms=False
    )
    
    # Result contains prepared messages
    print(result['email_prepared'])  # True
    print(result['notifications_sent'])  # List of prepared notifications
```

### In Serializer

```python
# apps/patients/serializers.py

from apps.patients.portal_notifications import notify_new_portal_account

class PatientCreateSerializer(serializers.ModelSerializer):
    
    def create(self, validated_data):
        # ... patient creation logic ...
        
        if portal_created:
            # Send notification
            notify_new_portal_account(
                patient=patient,
                username=portal_email,
                temporary_password=temporary_password,
                phone=portal_phone  # Optional
            )
        
        return patient
```

### Convenience Function

```python
from apps.patients.portal_notifications import notify_new_portal_account

# Simplest usage
notify_new_portal_account(
    patient=patient,
    username='jane@example.com',
    temporary_password='aB3dE5fG7h'
)
```

---

## Message Format

### Email Message

**Subject:**
```
Welcome to [Clinic Name] Patient Portal
```

**Body:**
```
Dear John Doe,

Your patient portal account has been created successfully.

LOGIN CREDENTIALS:
------------------
Username: john@example.com
Temporary Password: xK9mP2nQ7vR3
Portal URL: https://yoursite.com/patient-portal/login

IMPORTANT: Please change your password after your first login for security.

What you can do in the Patient Portal:
• View your medical records
• Check lab results
• View prescriptions
• See upcoming appointments
• View bills and payment status
• Update your contact information

If you have any questions, please contact our reception desk.

Best regards,
[Clinic Name]

---
This is an automated message. Please do not reply to this email.
```

### SMS Message

```
Your patient portal account has been created.

Login: john@example.com
Temporary Password: xK9mP2nQ7vR3
Please change it after login.

[Clinic Name]
```

**Character count:** ~150 characters (SMS-friendly)

---

## Function Reference

### 1. `prepare_portal_welcome_message()`

**Purpose:** Prepare formatted messages for portal account creation

**Parameters:**
- `patient_name` (str): Full name of patient
- `username` (str): Portal username/email
- `temporary_password` (str): 12-character password
- `login_url` (str): Portal login path (default: '/patient-portal/login')

**Returns:**
```python
{
    'subject': 'Welcome to ...',
    'email_body': 'Dear ...',
    'sms_body': 'Your patient portal ...',
    'login_url': 'https://...'
}
```

**Example:**
```python
messages = prepare_portal_welcome_message(
    patient_name='John Doe',
    username='john@example.com',
    temporary_password='xK9mP2nQ7vR3'
)

print(messages['subject'])
print(messages['email_body'])
print(messages['sms_body'])
```

---

### 2. `notify_portal_account_created()`

**Purpose:** Main notification function - prepares and logs notifications

**Parameters:**
- `patient` (Patient): Patient model instance
- `username` (str): Portal username
- `temporary_password` (str): Generated password
- `send_email` (bool): Prepare email notification (default: True)
- `send_sms` (bool): Prepare SMS notification (default: False)
- `phone_number` (str): Phone for SMS (optional)

**Returns:**
```python
{
    'success': True,
    'patient_id': 123,
    'patient_name': 'John Doe',
    'username': 'john@example.com',
    'notifications_sent': [
        {
            'type': 'email',
            'to': 'john@example.com',
            'subject': '...',
            'body': '...',
            'status': 'prepared'
        }
    ],
    'email_prepared': True,
    'sms_prepared': False
}
```

**Example:**
```python
result = notify_portal_account_created(
    patient=patient,
    username='john@example.com',
    temporary_password='xK9mP2nQ7vR3',
    send_email=True,
    send_sms=True,
    phone_number='0712345678'
)

if result['email_prepared']:
    print("Email notification prepared")

if result['sms_prepared']:
    print("SMS notification prepared")
```

---

### 3. `notify_new_portal_account()`

**Purpose:** Convenience wrapper - simplifies common usage

**Parameters:**
- `patient` (Patient): Patient instance
- `username` (str): Portal username
- `temporary_password` (str): Temporary password
- `email` (str): Email address (optional, defaults to username)
- `phone` (str): Phone number (optional)

**Returns:** Same as `notify_portal_account_created()`

**Example:**
```python
# Simplest usage
notify_new_portal_account(
    patient=patient,
    username='john@example.com',
    temporary_password='xK9mP2nQ7vR3'
)

# With SMS
notify_new_portal_account(
    patient=patient,
    username='john@example.com',
    temporary_password='xK9mP2nQ7vR3',
    phone='0712345678'
)
```

---

### 4. `send_portal_password_reset()`

**Purpose:** Prepare password reset notifications

**Parameters:**
- `patient` (Patient): Patient instance
- `username` (str): Portal username
- `reset_token` (str): Password reset token
- `reset_url` (str): Full reset URL with token

**Returns:**
```python
{
    'success': True,
    'patient_id': 123,
    'username': 'john@example.com',
    'reset_url': 'https://...',
    'email_prepared': True
}
```

---

### 5. `send_portal_appointment_reminder()`

**Purpose:** Prepare appointment reminder notifications

**Parameters:**
- `patient` (Patient): Patient instance
- `appointment_datetime` (str): Formatted date/time
- `doctor_name` (str): Doctor's name
- `clinic_location` (str): Location (optional)

**Returns:** Notification result dictionary

---

### 6. `send_lab_result_notification()`

**Purpose:** Notify patient when lab results are available

**Parameters:**
- `patient` (Patient): Patient instance
- `test_name` (str): Name of lab test
- `result_url` (str): URL to view results

**Returns:** Notification result dictionary

---

## Configuration

### Settings Required

Add to `backend/core/settings.py`:

```python
# Clinic Information
CLINIC_NAME = 'Modern Medical Center'
BASE_URL = 'https://yoursite.com'  # Or http://localhost:3000 for dev

# Email Configuration (for future integration)
DEFAULT_FROM_EMAIL = 'noreply@yoursite.com'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'

# SMS Configuration (for future integration)
TWILIO_ACCOUNT_SID = 'your_twilio_sid'
TWILIO_AUTH_TOKEN = 'your_twilio_token'
TWILIO_PHONE_NUMBER = '+1234567890'
```

---

## Integration in Serializer

### Add to `PatientCreateSerializer.create()`

```python
def create(self, validated_data):
    # ... existing portal creation code ...
    
    if portal_created:
        # Import notification utility
        from apps.patients.portal_notifications import notify_new_portal_account
        
        try:
            # Send notification
            notify_result = notify_new_portal_account(
                patient=patient,
                username=portal_email,
                temporary_password=temporary_password,
                phone=portal_phone
            )
            
            logger.info(
                f"Portal notifications prepared for patient {patient.id}: "
                f"{len(notify_result['notifications_sent'])} notification(s)"
            )
            
        except Exception as e:
            # Don't fail patient creation if notification fails
            logger.error(f"Failed to prepare portal notifications: {str(e)}")
    
    return patient
```

---

## Logging Output

### Development Mode (DEBUG=True)

```
[INFO] Portal account email prepared for John Doe (Patient ID: 123, Email: john@example.com)
[DEBUG] Email subject: Welcome to Our Clinic Patient Portal
[DEBUG] Email body preview: Dear John Doe, Your patient portal account has been created successfully...
[INFO] [DEV ONLY] Portal credentials for John Doe: Username=john@example.com, Password=xK9mP2nQ7vR3
```

### Production Mode (DEBUG=False)

```
[INFO] Portal account email prepared for John Doe (Patient ID: 123, Email: john@example.com)
[INFO] Portal account SMS prepared for John Doe (Patient ID: 123, Phone: 0712345678)
```

**Note:** Credentials are NOT logged in production for security.

---

## Future Email Integration

### Option 1: Django Built-in

```python
def _send_email(to: str, subject: str, body: str) -> bool:
    from django.core.mail import send_mail
    
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Email failed: {e}")
        return False
```

### Option 2: SendGrid

```python
def _send_email(to: str, subject: str, body: str) -> bool:
    import sendgrid
    from sendgrid.helpers.mail import Mail
    
    try:
        sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        message = Mail(
            from_email=settings.DEFAULT_FROM_EMAIL,
            to_emails=to,
            subject=subject,
            plain_text_content=body
        )
        response = sg.send(message)
        return response.status_code == 202
    except Exception as e:
        logger.error(f"SendGrid failed: {e}")
        return False
```

### Option 3: AWS SES

```python
def _send_email(to: str, subject: str, body: str) -> bool:
    import boto3
    
    try:
        client = boto3.client('ses', region_name=settings.AWS_REGION)
        response = client.send_email(
            Source=settings.DEFAULT_FROM_EMAIL,
            Destination={'ToAddresses': [to]},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Text': {'Data': body}}
            }
        )
        return True
    except Exception as e:
        logger.error(f"AWS SES failed: {e}")
        return False
```

---

## Future SMS Integration

### Option 1: Twilio

```python
def _send_sms(to: str, body: str) -> bool:
    from twilio.rest import Client
    
    try:
        client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )
        
        message = client.messages.create(
            body=body,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=to
        )
        
        return message.sid is not None
    except Exception as e:
        logger.error(f"Twilio SMS failed: {e}")
        return False
```

### Option 2: Africa's Talking

```python
def _send_sms(to: str, body: str) -> bool:
    import africastalking
    
    try:
        africastalking.initialize(
            username=settings.AFRICASTALKING_USERNAME,
            api_key=settings.AFRICASTALKING_API_KEY
        )
        
        sms = africastalking.SMS
        response = sms.send(body, [to])
        
        return response['SMSMessageData']['Recipients'][0]['status'] == 'Success'
    except Exception as e:
        logger.error(f"Africa's Talking failed: {e}")
        return False
```

---

## Testing

### Test Notification Preparation

```python
from apps.patients.models import Patient
from apps.patients.portal_notifications import notify_portal_account_created

# Get test patient
patient = Patient.objects.first()

# Prepare notification
result = notify_portal_account_created(
    patient=patient,
    username='test@example.com',
    temporary_password='testPass123',
    send_email=True,
    send_sms=True,
    phone_number='0712345678'
)

# Check result
print(f"Success: {result['success']}")
print(f"Notifications prepared: {len(result['notifications_sent'])}")

for notification in result['notifications_sent']:
    print(f"\nType: {notification['type']}")
    print(f"To: {notification['to']}")
    if notification['type'] == 'email':
        print(f"Subject: {notification['subject']}")
    print(f"Body preview: {notification['body'][:100]}...")
```

### Expected Output

```
Success: True
Notifications prepared: 2

Type: email
To: test@example.com
Subject: Welcome to Our Clinic Patient Portal
Body preview: Dear John Doe,

Your patient portal account has been created successfully.

LOGIN CREDENTIALS...

Type: sms
To: 0712345678
Body preview: Your patient portal account has been created.

Login: test@example.com
Temporary Password: testPass...
```

---

## Return Data Structure

### `notify_portal_account_created()` Returns

```python
{
    'success': True,
    'patient_id': 123,
    'patient_name': 'John Doe',
    'username': 'john@example.com',
    'notifications_sent': [
        {
            'type': 'email',
            'to': 'john@example.com',
            'subject': 'Welcome to Our Clinic Patient Portal',
            'body': 'Dear John Doe, Your patient portal...',
            'status': 'prepared'
        },
        {
            'type': 'sms',
            'to': '0712345678',
            'body': 'Your patient portal account...',
            'status': 'prepared'
        }
    ],
    'email_prepared': True,
    'sms_prepared': True
}
```

---

## Notification Types

### 1. Portal Account Created
```python
notify_portal_account_created(patient, username, password)
```
- Welcome message
- Login credentials
- Instructions

### 2. Password Reset
```python
send_portal_password_reset(patient, username, token, url)
```
- Reset link
- Expiry information
- Security note

### 3. Appointment Reminder
```python
send_portal_appointment_reminder(patient, datetime, doctor, location)
```
- Appointment details
- Arrival instructions
- Portal link

### 4. Lab Results Available
```python
send_lab_result_notification(patient, test_name, url)
```
- Test name
- Results link
- Doctor contact info

---

## Logging Levels

### INFO
```python
logger.info("Portal account email prepared for John Doe")
logger.info("SMS notification prepared for 0712345678")
```

### DEBUG
```python
logger.debug(f"Email subject: {subject}")
logger.debug(f"Email body preview: {body[:100]}")
```

### WARNING
```python
logger.warning("Email service not configured")
```

### ERROR
```python
logger.error(f"Failed to send email: {str(e)}")
```

---

## Configuration Options

### Required Settings

```python
# settings.py

# Clinic branding
CLINIC_NAME = 'Modern Medical Center'

# URLs
BASE_URL = 'https://yoursite.com'  # Production
# BASE_URL = 'http://localhost:3000'  # Development
```

### Optional Settings

```python
# Email (for future)
DEFAULT_FROM_EMAIL = 'noreply@yoursite.com'
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# SMS (for future)
SMS_BACKEND = 'twilio'  # or 'africastalking', 'aws_sns'

# Notification preferences
PORTAL_NOTIFICATION_EMAIL_ENABLED = True
PORTAL_NOTIFICATION_SMS_ENABLED = False
```

---

## Error Handling

### Graceful Degradation

```python
try:
    notify_new_portal_account(...)
except Exception as e:
    # Log error but don't fail patient creation
    logger.error(f"Notification failed: {e}")
    # Patient and user still created successfully
```

**Philosophy:** Notification failures should NEVER prevent patient registration.

---

## Integration Checklist

### ✅ Current Status
- ✅ Message preparation functions
- ✅ Structured return data
- ✅ Logging configured
- ✅ Error handling
- ✅ Multiple notification types
- ✅ SMS-friendly message length

### 🔜 To Enable Email
1. Configure Django email settings
2. Uncomment `_send_email()` implementation
3. Update `notify_portal_account_created()` to call `_send_email()`
4. Test with real email address

### 🔜 To Enable SMS
1. Choose SMS provider (Twilio, Africa's Talking, etc.)
2. Install provider SDK: `pip install twilio`
3. Configure credentials in settings
4. Uncomment `_send_sms()` implementation
5. Update `notify_portal_account_created()` to call `_send_sms()`
6. Test with real phone number

---

## Testing Checklist

### Message Preparation
- [ ] Email subject generated correctly
- [ ] Email body includes all credentials
- [ ] SMS body under 160 characters
- [ ] Login URL is absolute
- [ ] Patient name formatted correctly
- [ ] Clinic name from settings

### Function Returns
- [ ] Returns success flag
- [ ] Includes patient info
- [ ] Contains prepared notifications
- [ ] Email/SMS flags correct
- [ ] No exceptions raised

### Logging
- [ ] INFO logs created
- [ ] DEBUG logs in dev mode
- [ ] Credentials logged in dev only
- [ ] Errors logged properly

---

## Files

**Created:**
- `backend/apps/patients/portal_notifications.py` (~250 lines)

**Documentation:**
- `PORTAL_NOTIFICATION_UTILITY.md` (this file)

---

## Next Steps

### Immediate
1. ✅ Utility created
2. ✅ Messages structured
3. ✅ Ready for integration

### When Ready for Email
1. Add to `requirements.txt`: 
   ```
   sendgrid>=6.9.0
   # or use Django's built-in email
   ```
2. Configure settings (EMAIL_HOST, etc.)
3. Uncomment `_send_email()` implementation
4. Call from serializer

### When Ready for SMS
1. Add to `requirements.txt`:
   ```
   twilio>=8.0.0
   # or africastalking>=1.2.0
   ```
2. Configure credentials
3. Uncomment `_send_sms()` implementation
4. Call from serializer

---

## Summary

**Status:** ✅ Complete and ready for integration

**What it does:**
- ✅ Prepares portal welcome messages
- ✅ Structures email and SMS content
- ✅ Logs preparation for debugging
- ✅ Returns notification details
- ✅ Handles multiple notification types

**What it doesn't do (yet):**
- ❌ Actually send emails (integration needed)
- ❌ Actually send SMS (integration needed)
- ❌ Retry failed notifications
- ❌ Queue notifications

**Integration effort:**
- Email: ~10 minutes (configure Django email)
- SMS: ~20 minutes (set up Twilio/provider)
- Testing: ~5 minutes per service

---

**File:** `backend/apps/patients/portal_notifications.py`  
**Lines:** 250  
**Functions:** 6  
**Status:** ✅ Ready for use

🎉 **Notification utility is complete and ready for integration!**

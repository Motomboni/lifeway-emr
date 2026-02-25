"""
SMS notification utilities.

Per EMR Rules:
- PHI data must be protected
- All notifications must be logged
- Audit logging mandatory
"""
import logging
from django.conf import settings
from .models import EmailNotification  # Reuse EmailNotification model for SMS tracking

logger = logging.getLogger(__name__)


def send_sms_notification(
    phone_number,
    message,
    notification_type='SYSTEM_ALERT',
    appointment=None,
    visit=None,
    created_by=None,
):
    """
    Send an SMS notification.
    
    Args:
        phone_number: Phone number to send SMS to (E.164 format recommended)
        message: SMS message text
        notification_type: Type of notification
        appointment: Optional related appointment
        visit: Optional related visit
        created_by: Optional user who triggered the notification
    
    Returns:
        EmailNotification: The created notification record (reused for SMS tracking)
    """
    from django.utils import timezone
    
    # Create notification record (reusing EmailNotification model)
    notification = EmailNotification.objects.create(
        notification_type=notification_type,
        status='PENDING',
        recipient_email=phone_number,  # Store phone number in email field for SMS
        recipient_name='',
        appointment=appointment,
        visit=visit,
        subject='SMS Notification',
        email_body=message,
        created_by=created_by,
    )
    
    try:
        # Check if SMS is enabled
        sms_enabled = getattr(settings, 'SMS_ENABLED', False)
        if not sms_enabled:
            logger.info(f"SMS disabled, skipping SMS to {phone_number}")
            notification.status = 'CANCELLED'
            notification.save(update_fields=['status'])
            return notification
        
        # Get SMS provider from settings
        sms_provider = getattr(settings, 'SMS_PROVIDER', 'console')
        
        if sms_provider == 'twilio':
            _send_via_twilio(phone_number, message, notification)
        elif sms_provider == 'termii':
            _send_via_termii(phone_number, message, notification)
        elif sms_provider == 'console':
            # Console backend for development
            logger.info(f"[SMS] To: {phone_number}, Message: {message}")
            notification.status = 'SENT'
            notification.sent_at = timezone.now()
            notification.save(update_fields=['status', 'sent_at'])
        else:
            logger.warning(f"Unknown SMS provider: {sms_provider}")
            notification.status = 'FAILED'
            notification.error_message = f"Unknown SMS provider: {sms_provider}"
            notification.save(update_fields=['status', 'error_message'])
        
    except Exception as e:
        # Log failure
        notification.status = 'FAILED'
        notification.error_message = str(e)
        notification.save(update_fields=['status', 'error_message'])
        logger.error(f"Failed to send SMS: {e}")
        raise
    
    return notification


def _send_via_twilio(phone_number, message, notification):
    """
    Send SMS via Twilio.
    
    Requires:
    - TWILIO_ACCOUNT_SID in settings
    - TWILIO_AUTH_TOKEN in settings
    - TWILIO_PHONE_NUMBER in settings
    """
    try:
        from twilio.rest import Client
        from django.utils import timezone
        
        account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        from_number = getattr(settings, 'TWILIO_PHONE_NUMBER', None)
        
        if not all([account_sid, auth_token, from_number]):
            raise ValueError("Twilio credentials not configured")
        
        client = Client(account_sid, auth_token)
        
        message_obj = client.messages.create(
            body=message,
            from_=from_number,
            to=phone_number
        )
        
        notification.status = 'SENT'
        notification.sent_at = timezone.now()
        notification.save(update_fields=['status', 'sent_at'])
        
        logger.info(f"SMS sent via Twilio: {message_obj.sid}")
        
    except ImportError:
        raise ImportError("twilio package not installed. Install with: pip install twilio")
    except Exception as e:
        raise Exception(f"Twilio SMS error: {e}")


def _send_via_termii(phone_number, message, notification):
    """
    Send SMS via Termii (Nigeria-focused provider).
    Uses DND channel for transactional messages (OTPs, reminders, etc.).

    Requires:
    - TERMII_API_KEY in settings
    - TERMII_SENDER_ID in settings (alphanumeric, 3-11 chars)
    - TERMII_BASE_URL in settings (per-account, default api.termii.com)
    """
    import requests
    from django.utils import timezone

    api_key = getattr(settings, 'TERMII_API_KEY', None)
    sender_id = getattr(settings, 'TERMII_SENDER_ID', None)
    base_url = getattr(settings, 'TERMII_BASE_URL', 'https://api.termii.com').rstrip('/')

    if not api_key or not sender_id:
        raise ValueError("Termii credentials not configured (TERMII_API_KEY, TERMII_SENDER_ID)")

    # Termii expects 2348012345678 format (no +)
    to_number = phone_number.lstrip('+').replace(' ', '')

    url = f"{base_url}/api/sms/send"
    payload = {
        'api_key': api_key,
        'to': to_number,
        'from': sender_id,
        'sms': message,
        'type': 'plain',
        'channel': 'dnd',  # Transactional - bypasses DND, no time restrictions
    }

    response = requests.post(url, json=payload, timeout=30)
    try:
        data = response.json() if response.text else {}
    except Exception:
        data = {}

    if response.ok and data.get('code') == 'ok':
        notification.status = 'SENT'
        notification.sent_at = timezone.now()
        notification.save(update_fields=['status', 'sent_at'])
        logger.info(f"SMS sent via Termii: {data.get('message_id', '')}")
    else:
        error_msg = data.get('message', data.get('error', response.text)) or str(response.status_code)
        raise Exception(f"Termii SMS error: {error_msg}")


def send_appointment_reminder_sms(appointment):
    """Send appointment reminder SMS."""
    patient = appointment.patient
    doctor = appointment.doctor
    
    if not patient.phone:
        return None
    
    message = (
        f"Appointment Reminder: {appointment.appointment_date.strftime('%B %d, %Y')} "
        f"at {appointment.appointment_date.strftime('%I:%M %p')} with Dr. {doctor.last_name}. "
        f"Please arrive 15 minutes early."
    )
    
    return send_sms_notification(
        phone_number=patient.phone,
        message=message,
        notification_type='APPOINTMENT_REMINDER',
        appointment=appointment,
        created_by=appointment.created_by,
    )


def send_lab_result_sms(lab_result):
    """Send lab result ready SMS."""
    visit = lab_result.lab_order.visit
    patient = visit.patient
    
    if not patient.phone:
        return None
    
    message = (
        f"Your lab results from {visit.created_at.strftime('%B %d, %Y')} are ready. "
        f"Please contact your doctor. Lab Order #{lab_result.lab_order.id}"
    )
    
    return send_sms_notification(
        phone_number=patient.phone,
        message=message,
        notification_type='LAB_RESULT_READY',
        visit=visit,
    )


def send_radiology_result_sms(radiology_result):
    """Send radiology result ready SMS."""
    visit = radiology_result.radiology_order.visit
    patient = visit.patient
    
    if not patient.phone:
        return None
    
    message = (
        f"Your radiology results from {visit.created_at.strftime('%B %d, %Y')} are ready. "
        f"Please contact your doctor. Radiology Order #{radiology_result.radiology_order.id}"
    )
    
    return send_sms_notification(
        phone_number=patient.phone,
        message=message,
        notification_type='RADIOLOGY_RESULT_READY',
        visit=visit,
    )

"""
OTP Utility Functions

WhatsApp, SMS, and Email OTP sending stubs.
Ready for integration with real services.
"""
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def normalize_nigerian_phone(phone: str) -> Optional[str]:
    """
    Normalize Nigerian phone number to +234 format.
    
    Accepts:
    - 0801234567 → +2348012345678
    - 08012345678 → +2348012345678
    - 2348012345678 → +2348012345678
    - +2348012345678 → +2348012345678
    
    Returns:
        Normalized phone in +234 format or None if invalid
    """
    if not phone:
        return None
    
    # Remove all non-digit characters except +
    phone = re.sub(r'[^\d+]', '', phone)
    
    # Remove leading zeros
    phone = phone.lstrip('0')
    
    # Remove + if present
    phone = phone.lstrip('+')
    
    # Handle different formats
    if phone.startswith('234'):
        # Already has country code
        return f"+{phone}"
    elif len(phone) == 10:
        # Nigerian number without country code (e.g., 8012345678)
        return f"+234{phone}"
    elif len(phone) == 11 and phone.startswith('0'):
        # With leading zero (e.g., 08012345678) - strip it
        return f"+234{phone[1:]}"
    else:
        logger.warning(f"Could not normalize phone number: {phone}")
        return None


def send_email_otp(email: str, otp_code: str, patient_name: str = '') -> bool:
    """
    Send OTP via email.
    
    This is a stub function. Integrate with real email service:
    - Django send_mail
    - SendGrid
    - AWS SES
    - Mailgun
    
    Args:
        email: Recipient email
        otp_code: 6-digit OTP
        patient_name: Patient name for personalization
    
    Returns:
        True if sent successfully, False otherwise
    """
    from django.conf import settings
    
    clinic_name = getattr(settings, 'CLINIC_NAME', 'Our Clinic')
    
    subject = f"{clinic_name} - Login Code"
    
    greeting = f"Dear {patient_name}," if patient_name else "Hello,"
    
    message = f"""{greeting}

Your login code is: {otp_code}

This code will expire in 5 minutes.

If you did not request this code, please ignore this email.

Best regards,
{clinic_name}
"""
    
    try:
        # TODO: Integrate with real email service
        """
        from django.core.mail import send_mail
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        """
        
        logger.info(f"[EMAIL OTP] Sent to {email}: {otp_code}")
        
        # Development: Log OTP for testing
        if settings.DEBUG:
            logger.info(f"[DEV] OTP for {email}: {otp_code}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email OTP to {email}: {e}")
        return False


def send_sms_otp(phone: str, otp_code: str) -> bool:
    """
    Send OTP via SMS.
    
    This is a stub function. Integrate with real SMS service:
    - Twilio
    - Africa's Talking
    - AWS SNS
    - Vonage/Nexmo
    
    Args:
        phone: Recipient phone (+234 format)
        otp_code: 6-digit OTP
    
    Returns:
        True if sent successfully, False otherwise
    """
    from django.conf import settings
    
    clinic_name = getattr(settings, 'CLINIC_NAME', 'Our Clinic')
    
    # Normalize phone
    normalized_phone = normalize_nigerian_phone(phone)
    if not normalized_phone:
        logger.error(f"Invalid phone number format: {phone}")
        return False
    
    message = f"Your {clinic_name} login code is: {otp_code}\n\nValid for 5 minutes."
    
    try:
        # TODO: Integrate with real SMS service
        """
        from twilio.rest import Client
        
        client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )
        
        client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=normalized_phone
        )
        """
        
        logger.info(f"[SMS OTP] Sent to {normalized_phone}: {otp_code}")
        
        if settings.DEBUG:
            logger.info(f"[DEV] SMS OTP for {normalized_phone}: {otp_code}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send SMS OTP to {normalized_phone}: {e}")
        return False


def send_whatsapp_otp(phone: str, otp_code: str, patient_name: str = '') -> bool:
    """
    Send OTP via WhatsApp.
    
    This is a stub function. Integrate with WhatsApp Business API:
    - Twilio WhatsApp
    - Meta (Facebook) WhatsApp Business API
    - Third-party providers (e.g., MessageBird, Vonage)
    
    Args:
        phone: Recipient phone (+234 format)
        otp_code: 6-digit OTP
        patient_name: Patient name for personalization
    
    Returns:
        True if sent successfully, False otherwise
    """
    from django.conf import settings
    
    clinic_name = getattr(settings, 'CLINIC_NAME', 'Our Clinic')
    
    # Normalize phone
    normalized_phone = normalize_nigerian_phone(phone)
    if not normalized_phone:
        logger.error(f"Invalid phone number for WhatsApp: {phone}")
        return False
    
    greeting = f"Hello {patient_name}!" if patient_name else "Hello!"
    
    message = f"""{greeting}

Your {clinic_name} login code is:

*{otp_code}*

This code will expire in 5 minutes.

If you did not request this code, please ignore this message.
"""
    
    try:
        # TODO: Integrate with WhatsApp Business API
        """
        # Option 1: Twilio WhatsApp
        from twilio.rest import Client
        
        client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )
        
        client.messages.create(
            body=message,
            from_=f'whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}',
            to=f'whatsapp:{normalized_phone}'
        )
        
        # Option 2: Meta WhatsApp Business API
        import requests
        
        response = requests.post(
            f'https://graph.facebook.com/v17.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages',
            headers={
                'Authorization': f'Bearer {settings.WHATSAPP_ACCESS_TOKEN}',
                'Content-Type': 'application/json'
            },
            json={
                'messaging_product': 'whatsapp',
                'to': normalized_phone,
                'type': 'template',
                'template': {
                    'name': 'otp_code',
                    'language': {'code': 'en'},
                    'components': [
                        {
                            'type': 'body',
                            'parameters': [{'type': 'text', 'text': otp_code}]
                        }
                    ]
                }
            }
        )
        """
        
        logger.info(f"[WHATSAPP OTP] Sent to {normalized_phone}: {otp_code}")
        
        if settings.DEBUG:
            logger.info(f"[DEV] WhatsApp OTP for {normalized_phone}: {otp_code}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send WhatsApp OTP to {normalized_phone}: {e}")
        return False


def get_client_ip(request) -> Optional[str]:
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_device_type(user_agent: str) -> str:
    """
    Determine device type from user agent string.
    
    Returns: 'ios', 'android', 'web', or 'unknown'
    """
    if not user_agent:
        return 'unknown'
    
    user_agent_lower = user_agent.lower()
    
    if 'iphone' in user_agent_lower or 'ipad' in user_agent_lower:
        return 'ios'
    elif 'android' in user_agent_lower:
        return 'android'
    elif 'mozilla' in user_agent_lower or 'chrome' in user_agent_lower:
        return 'web'
    else:
        return 'unknown'

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
    phone = re.sub(r"[^\d+]", "", phone)

    # Remove leading zeros
    phone = phone.lstrip("0")

    # Remove + if present
    phone = phone.lstrip("+")

    # Handle different formats
    if phone.startswith("234"):
        # Already has country code
        return f"+{phone}"
    elif len(phone) == 10:
        # Nigerian number without country code (e.g., 8012345678)
        return f"+234{phone}"
    elif len(phone) == 11 and phone.startswith("0"):
        # With leading zero (e.g., 08012345678) - strip it
        return f"+234{phone[1:]}"
    else:
        logger.warning(f"Could not normalize phone number: {phone}")
        return None


def send_email_otp(email: str, otp_code: str, patient_name: str = "") -> bool:
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

    clinic_name = getattr(settings, "CLINIC_NAME", "Our Clinic")

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
        from django.core.mail import send_mail

        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@emr.local"),
            recipient_list=[email],
            fail_silently=False,
        )

        if settings.DEBUG:
            logger.info("[DEV] OTP for %s: %s", email, otp_code)

        return True

    except Exception as e:
        logger.error(f"Failed to send email OTP to {email}: {e}")
        return False


def send_sms_otp(phone: str, otp_code: str) -> bool:
    """
    Send OTP via SMS using the configured SMS provider (Termii, Twilio, or console).

    Args:
        phone: Recipient phone (+234 or local format)
        otp_code: 6-digit OTP

    Returns:
        True if sent successfully, False otherwise
    """
    from django.conf import settings

    clinic_name = getattr(settings, "CLINIC_NAME", "Our Clinic")

    # Normalize phone
    normalized_phone = normalize_nigerian_phone(phone)
    if not normalized_phone:
        logger.error(f"Invalid phone number format: {phone}")
        return False

    message = f"Your {clinic_name} login code is: {otp_code}\n\nValid for 5 minutes."

    try:
        from apps.notifications.nigeria_comms import send_otp_sms

        notification = send_otp_sms(normalized_phone, otp_code)
        ok = notification is not None and getattr(notification, "status", "") == "SENT"

        if settings.DEBUG and ok:
            logger.info(f"[DEV] SMS OTP for {normalized_phone}: {otp_code}")
        elif settings.DEBUG and not ok:
            logger.info(
                f"[DEV] SMS disabled/cancelled, OTP for {normalized_phone}: {otp_code}"
            )

        return ok or settings.DEBUG

    except Exception as e:
        logger.error(f"Failed to send SMS OTP to {normalized_phone}: {e}")
        return False


def send_whatsapp_otp(phone: str, otp_code: str, patient_name: str = "") -> bool:
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

    clinic_name = getattr(settings, "CLINIC_NAME", "Our Clinic")

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
        from apps.notifications.whatsapp_service import send_whatsapp_message

        ok = send_whatsapp_message(normalized_phone, message.strip())

        if settings.DEBUG:
            logger.info(f"[DEV] WhatsApp OTP for {normalized_phone}: {otp_code}")

        return ok

    except Exception as e:
        logger.error(f"Failed to send WhatsApp OTP to {normalized_phone}: {e}")
        return False


def get_client_ip(request) -> Optional[str]:
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def get_device_type(user_agent: str) -> str:
    """
    Determine device type from user agent string.

    Returns: 'ios', 'android', 'web', or 'unknown'
    """
    if not user_agent:
        return "unknown"

    user_agent_lower = user_agent.lower()

    if "iphone" in user_agent_lower or "ipad" in user_agent_lower:
        return "ios"
    elif "android" in user_agent_lower:
        return "android"
    elif "mozilla" in user_agent_lower or "chrome" in user_agent_lower:
        return "web"
    else:
        return "unknown"

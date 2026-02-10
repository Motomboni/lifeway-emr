"""
WhatsApp message service - stub for sending appointment reminders.

In production, integrate with WhatsApp Business API (e.g. Twilio WhatsApp,
Meta Cloud API, or a local provider for Nigeria).
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def send_whatsapp_message(phone: str, message: str) -> bool:
    """
    Send a WhatsApp message to the given phone number.

    Stub implementation. Replace with real integration (Twilio WhatsApp,
    Meta Cloud API, etc.). Nigerian numbers: ensure E.164 format (e.g. +2348012345678).

    Args:
        phone: Recipient phone (E.164 preferred).
        message: Plain text message.

    Returns:
        True if send succeeded (or stub), False on failure.
    """
    logger.info(
        "WhatsApp stub: would send to %s: %s",
        phone[:6] + "***" if len(phone) > 6 else phone,
        message[:80] + "..." if len(message) > 80 else message,
    )
    if getattr(settings, 'WHATSAPP_STUB_ALWAYS_FAIL', False):
        return False
    return True

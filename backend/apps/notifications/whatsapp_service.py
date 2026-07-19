"""
WhatsApp message service — Termii WhatsApp channel or Meta Cloud API stub.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_whatsapp_message(phone: str, message: str) -> bool:
    provider = getattr(settings, "WHATSAPP_PROVIDER", "stub").lower()
    if provider == "termii":
        return _send_via_termii_whatsapp(phone, message)
    if provider == "meta":
        return _send_via_meta(phone, message)
    logger.info(
        "WhatsApp stub: would send to %s: %s",
        phone[:6] + "***" if len(phone) > 6 else phone,
        message[:80] + "..." if len(message) > 80 else message,
    )
    return not getattr(settings, "WHATSAPP_STUB_ALWAYS_FAIL", False)


def _send_via_termii_whatsapp(phone: str, message: str) -> bool:
    api_key = getattr(settings, "TERMII_API_KEY", "")
    base_url = getattr(settings, "TERMII_BASE_URL", "https://api.termii.com").rstrip("/")
    if not api_key:
        logger.error("TERMII_API_KEY not configured for WhatsApp.")
        return False
    payload = {
        "api_key": api_key,
        "to": phone,
        "from": getattr(settings, "TERMII_WHATSAPP_SENDER", "Lifeway"),
        "type": "plain",
        "channel": "whatsapp",
        "sms": message,
    }
    try:
        resp = requests.post(f"{base_url}/api/sms/send", json=payload, timeout=20)
        return resp.status_code < 400
    except requests.RequestException as exc:
        logger.exception("Termii WhatsApp failed: %s", exc)
        return False


def _send_via_meta(phone: str, message: str) -> bool:
    token = getattr(settings, "WHATSAPP_META_TOKEN", "")
    phone_id = getattr(settings, "WHATSAPP_META_PHONE_ID", "")
    if not token or not phone_id:
        logger.error("WHATSAPP_META_TOKEN / WHATSAPP_META_PHONE_ID not configured.")
        return False
    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": phone.lstrip("+"),
        "type": "text",
        "text": {"body": message},
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=20)
        return resp.status_code < 400
    except requests.RequestException as exc:
        logger.exception("Meta WhatsApp failed: %s", exc)
        return False

"""
National Health ID verification (Nigeria-ready).

Modes (settings.NHID_VERIFICATION_MODE):
- stub: local dev — accepts valid-format IDs
- http: POST to NHID_API_URL with NHID_API_KEY header
"""

from __future__ import annotations

import logging
from typing import Tuple

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def verify_national_health_id(
    id_number: str,
    name: str,
    dob,
) -> Tuple[bool, str]:
    """
    Verify National Health ID against configured provider.

    Args:
        id_number: National Health ID / NIN number.
        name: Full name to match.
        dob: Date of birth (date object or string).

    Returns:
        (valid: bool, message: str)
    """
    id_number = (id_number or "").strip()
    name = (name or "").strip()
    if not id_number:
        return False, "ID number is required."
    if not name:
        return False, "Name is required."
    if len(id_number) < 8:
        return False, "Invalid ID format."

    mode = getattr(settings, "NHID_VERIFICATION_MODE", "stub").lower()
    if mode == "http":
        return _verify_via_http(id_number, name, dob)
    return _verify_stub(id_number, name, dob)


def _verify_stub(id_number: str, name: str, dob) -> Tuple[bool, str]:
    logger.info(
        "NHID verify stub: id=%s name=%s dob=%s",
        id_number[:4] + "***",
        name[:3] + "***",
        dob,
    )
    return True, "Verification successful (stub mode)."


def _verify_via_http(id_number: str, name: str, dob) -> Tuple[bool, str]:
    api_url = getattr(settings, "NHID_API_URL", "").strip()
    api_key = getattr(settings, "NHID_API_KEY", "").strip()
    if not api_url:
        logger.error("NHID_VERIFICATION_MODE=http but NHID_API_URL is not set.")
        return False, "NHID verification service is not configured."

    dob_str = str(dob) if dob else ""
    payload = {
        "id_number": id_number,
        "name": name,
        "date_of_birth": dob_str,
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=15)
    except requests.RequestException as exc:
        logger.exception("NHID HTTP verification failed: %s", exc)
        return False, "Unable to reach NHID verification service."

    if response.status_code == 404:
        return False, "National Health ID not found."
    if response.status_code >= 400:
        logger.warning(
            "NHID API error status=%s body=%s",
            response.status_code,
            response.text[:200],
        )
        return False, "NHID verification rejected by provider."

    try:
        data = response.json()
    except ValueError:
        return False, "Invalid response from NHID provider."

    valid = bool(data.get("valid") or data.get("verified"))
    message = data.get("message") or (
        "Verification successful." if valid else "Verification failed."
    )
    return valid, message

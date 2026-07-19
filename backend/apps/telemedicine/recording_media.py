"""
Resolve Twilio Video recording media to a downloadable URL for Whisper transcription.
"""

from __future__ import annotations

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def resolve_twilio_recording_download_url(recording_sid: str) -> str | None:
    """
    Resolve Twilio Video Recording SID to a temporary media download URL.

    Twilio Media subresource returns 302 Location or JSON { redirect_to }.
    """
    account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
    auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None)
    if not account_sid or not auth_token or not recording_sid:
        return None

    auth = (account_sid, auth_token)
    media_resource_url = (
        f"https://video.twilio.com/v1/Recordings/{recording_sid}/Media"
    )
    try:
        media_resp = requests.get(
            media_resource_url, auth=auth, timeout=30, allow_redirects=False
        )
        if media_resp.status_code == 302:
            return media_resp.headers.get("Location")
        if media_resp.status_code == 200:
            try:
                data = media_resp.json()
                return data.get("redirect_to") or data.get("redirectTo")
            except (ValueError, TypeError):
                return None
        if media_resp.status_code == 404:
            return None
    except requests.RequestException as exc:
        logger.warning("Twilio media resolve failed for %s: %s", recording_sid, exc)
    return None


def resolve_session_recording_download_url(session) -> str | None:
    """Best-effort download URL for a telemedicine session recording."""
    if session.recording_sid:
        url = resolve_twilio_recording_download_url(session.recording_sid)
        if url:
            return url
    # Legacy fallback — may not work for Whisper but try anyway
    return session.recording_url or None

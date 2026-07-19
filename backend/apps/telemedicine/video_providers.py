"""
Unified video provider facade for telemedicine (Twilio Video | LiveKit).

Set TELEMEDICINE_VIDEO_PROVIDER=twilio|livekit in environment.
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)

PROVIDER_TWILIO = "twilio"
PROVIDER_LIVEKIT = "livekit"


def get_active_video_provider() -> str:
    return (
        getattr(settings, "TELEMEDICINE_VIDEO_PROVIDER", PROVIDER_TWILIO) or PROVIDER_TWILIO
    ).lower().strip()


def resolve_session_video_provider(session) -> str:
    provider = getattr(session, "video_provider", None)
    if provider:
        return provider.lower()
    if (session.twilio_room_sid or "").startswith("RM"):
        return PROVIDER_TWILIO
    return get_active_video_provider()


def is_video_provider_configured(provider=None) -> bool:
    provider = (provider or get_active_video_provider()).lower()
    if provider == PROVIDER_LIVEKIT:
        return bool(
            getattr(settings, "LIVEKIT_URL", "")
            and getattr(settings, "LIVEKIT_API_KEY", "")
            and getattr(settings, "LIVEKIT_API_SECRET", "")
        )
    if provider == PROVIDER_TWILIO:
        return bool(
            getattr(settings, "TWILIO_ACCOUNT_SID", "")
            and getattr(settings, "TWILIO_AUTH_TOKEN", "")
            and getattr(settings, "TWILIO_API_KEY", "")
            and getattr(settings, "TWILIO_API_SECRET", "")
        )
    return False


def get_public_video_config(provider=None) -> dict:
    """Client-facing provider metadata (no secrets)."""
    provider = (provider or get_active_video_provider()).lower()
    payload = {"video_provider": provider}
    if provider == PROVIDER_LIVEKIT:
        from .livekit_utils import get_livekit_client_url

        try:
            payload["livekit_url"] = get_livekit_client_url()
        except ValueError:
            payload["livekit_url"] = ""
    return payload


def create_video_room(
    room_name,
    max_participants=2,
    record_participants_on_connect=False,
    provider=None,
):
    provider = (provider or get_active_video_provider()).lower()
    if provider == PROVIDER_LIVEKIT:
        from .livekit_utils import create_livekit_room

        info = create_livekit_room(
            room_name,
            max_participants=max_participants,
            record_participants_on_connect=record_participants_on_connect,
        )
    else:
        from .utils import create_twilio_room

        info = create_twilio_room(
            room_name,
            max_participants=max_participants,
            record_participants_on_connect=record_participants_on_connect,
        )
    info["video_provider"] = provider
    return info


def generate_video_access_token(user, room_name, room_sid=None, provider=None):
    provider = (provider or get_active_video_provider()).lower()
    if provider == PROVIDER_LIVEKIT:
        from .livekit_utils import generate_livekit_access_token

        return generate_livekit_access_token(user, room_name, room_sid)
    from .utils import generate_twilio_access_token

    return generate_twilio_access_token(
        user, room_name=room_name, room_sid=room_sid
    )


def end_video_room(room_sid, room_name=None, provider=None):
    provider = (provider or get_active_video_provider()).lower()
    if provider == PROVIDER_LIVEKIT:
        from .livekit_utils import end_livekit_room

        return end_livekit_room(room_sid, room_name=room_name)
    from .utils import end_twilio_room

    return end_twilio_room(room_sid)


def ensure_virtual_clinic_capacity(session, max_participants=None):
    """
    Raise provider room capacity so invited staff can join older 1:1 rooms.
    Best-effort: failures are logged and ignored so invites still succeed.
    """
    from .access import VIRTUAL_CLINIC_MAX_PARTICIPANTS

    target = max_participants or VIRTUAL_CLINIC_MAX_PARTICIPANTS
    provider = resolve_session_video_provider(session)
    try:
        if provider == PROVIDER_LIVEKIT:
            from .livekit_utils import update_livekit_room_max_participants

            return update_livekit_room_max_participants(
                session.twilio_room_name or session.twilio_room_sid,
                target,
            )
        from .utils import update_twilio_room_max_participants

        return update_twilio_room_max_participants(session.twilio_room_sid, target)
    except Exception as exc:
        logger.warning(
            "Could not raise room capacity for session %s (%s): %s",
            getattr(session, "id", None),
            provider,
            exc,
        )
        return None


def get_room_recordings_for_session(session):
    """Fetch recordings when supported (Twilio only today)."""
    provider = resolve_session_video_provider(session)
    if provider != PROVIDER_TWILIO:
        return []
    from .utils import get_room_recordings

    return get_room_recordings(session.twilio_room_sid)


def refresh_session_recording(session) -> bool:
    provider = resolve_session_video_provider(session)
    if provider != PROVIDER_TWILIO:
        return bool(session.recording_sid)
    from .utils import refresh_session_recording as twilio_refresh

    return twilio_refresh(session)

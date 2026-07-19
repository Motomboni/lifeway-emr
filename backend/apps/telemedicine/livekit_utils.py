"""
LiveKit video integration for telemedicine (self-hosted or LiveKit Cloud).

Alternative to Twilio Video — suited for single-clinic deployments.
"""

import asyncio
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

LIVEKIT_AVAILABLE = False

try:
    from livekit import api as livekit_api

    LIVEKIT_AVAILABLE = True
except ImportError:
    livekit_api = None
    logger.warning(
        "livekit-api not installed. Install with: pip install livekit-api"
    )


def _livekit_credentials():
    url = getattr(settings, "LIVEKIT_URL", "") or ""
    api_key = getattr(settings, "LIVEKIT_API_KEY", "") or ""
    api_secret = getattr(settings, "LIVEKIT_API_SECRET", "") or ""
    if not all([url, api_key, api_secret]):
        raise ValueError(
            "LiveKit credentials not configured (LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)"
        )
    return url, api_key, api_secret


def get_livekit_client_url() -> str:
    """WebSocket URL for livekit-client (browser)."""
    url, _, _ = _livekit_credentials()
    if url.startswith("https://"):
        return url.replace("https://", "wss://", 1)
    if url.startswith("http://"):
        return url.replace("http://", "ws://", 1)
    if not url.startswith("ws"):
        return f"wss://{url.lstrip('/')}"
    return url


def _api_url() -> str:
    url, _, _ = _livekit_credentials()
    if url.startswith("wss://"):
        return url.replace("wss://", "https://", 1)
    if url.startswith("ws://"):
        return url.replace("ws://", "http://", 1)
    if not url.startswith("http"):
        return f"https://{url.lstrip('/')}"
    return url


async def _create_room_async(room_name, max_participants=2):
    url, api_key, api_secret = _livekit_credentials()
    lkapi = livekit_api.LiveKitAPI(_api_url(), api_key, api_secret)
    try:
        room = await lkapi.room.create_room(
            livekit_api.CreateRoomRequest(
                name=room_name,
                empty_timeout=600,
                max_participants=max_participants,
            )
        )
        return room
    finally:
        await lkapi.aclose()


async def _delete_room_async(room_name):
    url, api_key, api_secret = _livekit_credentials()
    lkapi = livekit_api.LiveKitAPI(_api_url(), api_key, api_secret)
    try:
        await lkapi.room.delete_room(livekit_api.DeleteRoomRequest(room=room_name))
    except Exception as exc:
        logger.warning("LiveKit delete room %s: %s", room_name, exc)
    finally:
        await lkapi.aclose()


def create_livekit_room(room_name, max_participants=2, record_participants_on_connect=False):
    """
    Create a LiveKit room.

    Returns dict compatible with Twilio room_info shape.
    Server-side recording uses LiveKit Egress (configure separately on your LiveKit server).
    """
    if not LIVEKIT_AVAILABLE:
        raise ImportError(
            "livekit-api not installed. Install with: pip install livekit-api"
        )

    if record_participants_on_connect:
        logger.info(
            "LiveKit room %s: recording flag set — enable Room Egress on your LiveKit server for archives",
            room_name,
        )

    room = asyncio.run(_create_room_async(room_name, max_participants))
    sid = getattr(room, "sid", None) or room_name
    name = getattr(room, "name", None) or room_name
    logger.info("LiveKit room created sid=%s name=%s", sid, name)
    return {
        "room_sid": sid,
        "room_name": name,
        "status": "open",
    }


async def _update_room_async(room_name, max_participants):
    url, api_key, api_secret = _livekit_credentials()
    lkapi = livekit_api.LiveKitAPI(_api_url(), api_key, api_secret)
    try:
        # Recreate/update room settings — LiveKit upserts by name when possible
        room = await lkapi.room.create_room(
            livekit_api.CreateRoomRequest(
                name=room_name,
                empty_timeout=600,
                max_participants=max_participants,
            )
        )
        return room
    finally:
        await lkapi.aclose()


def update_livekit_room_max_participants(room_name, max_participants):
    """Best-effort raise of LiveKit room capacity for virtual clinic invites."""
    if not LIVEKIT_AVAILABLE:
        raise ImportError("livekit-api not installed")
    room = asyncio.run(_update_room_async(room_name, max_participants))
    sid = getattr(room, "sid", None) or room_name
    logger.info(
        "LiveKit room %s max_participants updated to %s", room_name, max_participants
    )
    return {"room_sid": sid, "max_participants": max_participants}


def end_livekit_room(room_sid, room_name=None):
    """Delete / close a LiveKit room."""
    if not LIVEKIT_AVAILABLE:
        raise ImportError("livekit-api not installed")

    target = room_name or room_sid
    asyncio.run(_delete_room_async(target))
    return {"room_sid": room_sid, "status": "completed"}


def generate_livekit_access_token(user, room_name, room_sid=None):
    """Generate a LiveKit JWT for joining a room."""
    if not LIVEKIT_AVAILABLE:
        raise ImportError("livekit-api not installed")

    _, api_key, api_secret = _livekit_credentials()
    room = room_name or room_sid
    if not room:
        raise ValueError("room_name is required for LiveKit token")

    display_name = f"{user.first_name} {user.last_name}".strip() or user.username
    token = livekit_api.AccessToken(api_key, api_secret)
    token.with_identity(str(user.id))
    token.with_name(display_name)
    token.with_grants(
        livekit_api.VideoGrants(
            room_join=True,
            room=room,
            can_publish=True,
            can_subscribe=True,
        )
    )
    jwt_token = token.to_jwt()
    logger.info("LiveKit token generated for user=%s room=%s", user.id, room)
    return jwt_token

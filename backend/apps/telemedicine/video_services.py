"""
Abstract video service for telemedicine.

Supports pluggable providers: Jitsi, Zoom, WebRTC (stub), or existing Twilio.
generate_video_room() returns room_id and meeting_link.
"""
import uuid
import logging
from abc import ABC, abstractmethod
from django.conf import settings

logger = logging.getLogger(__name__)


class BaseVideoService(ABC):
    """Abstract base for video room providers."""

    @abstractmethod
    def generate_video_room(self, room_name=None, max_participants=2, **kwargs):
        """
        Create a video room and return meeting details.

        Returns:
            dict: {
                "room_id": str (UUID or provider ID),
                "meeting_link": str (URL for patients/doctors to join),
                "extra": dict (provider-specific, e.g. access_token for Twilio)
            }
        """
        pass


class JitsiVideoService(BaseVideoService):
    """Jitsi Meet stub – returns public Jitsi meeting link."""

    def generate_video_room(self, room_name=None, max_participants=2, **kwargs):
        room_id = room_name or str(uuid.uuid4())
        base = getattr(settings, 'JITSI_MEET_SERVER', 'https://meet.jit.si')
        meeting_link = f"{base.rstrip('/')}/{room_id}"
        return {
            "room_id": room_id,
            "meeting_link": meeting_link,
            "extra": {},
        }


class ZoomVideoService(BaseVideoService):
    """Zoom stub – returns placeholder link (integrate Zoom API in production)."""

    def generate_video_room(self, room_name=None, max_participants=2, **kwargs):
        room_id = room_name or str(uuid.uuid4())
        # Stub: replace with Zoom API create meeting response
        meeting_link = f"https://zoom.us/j/{room_id}"
        return {
            "room_id": room_id,
            "meeting_link": meeting_link,
            "extra": {"join_url": meeting_link},
        }


class TwilioVideoService(BaseVideoService):
    """Twilio Video – uses existing utils; meeting_link is app URL that uses token."""

    def generate_video_room(self, room_name=None, max_participants=2, record_participants_on_connect=False, **kwargs):
        from .utils import create_twilio_room
        name = room_name or f"emr-{uuid.uuid4().hex[:12]}"
        room_info = create_twilio_room(
            room_name=name,
            max_participants=max_participants,
            record_participants_on_connect=record_participants_on_connect,
        )
        # Frontend typically opens /telemedicine/room/<session_id> and fetches token
        base_url = getattr(settings, 'FRONTEND_URL', '').rstrip('/')
        meeting_link = f"{base_url}/telemedicine/room/{kwargs.get('session_id', '')}" if base_url else room_info.get("room_name", name)
        return {
            "room_id": room_info["room_sid"],
            "meeting_link": meeting_link,
            "extra": {
                "room_sid": room_info["room_sid"],
                "room_name": room_info["room_name"],
            },
        }


def get_video_service():
    """Return configured video service (Jitsi stub, Zoom stub, or Twilio)."""
    provider = getattr(settings, 'TELEMEDICINE_VIDEO_PROVIDER', 'jitsi').lower()
    if provider == 'twilio':
        return TwilioVideoService()
    if provider == 'zoom':
        return ZoomVideoService()
    return JitsiVideoService()

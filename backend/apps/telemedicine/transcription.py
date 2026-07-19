"""
Telemedicine session transcription.

After a session with recording, transcription can be requested to produce
text from the recording. Configure a provider via settings:

- ``openai`` — OpenAI Whisper API (requires OPENAI_API_KEY)
- ``faster-whisper`` — local faster-whisper (no API key; requires ffmpeg)

Usage:
- Request transcription: POST /api/v1/telemedicine/{id}/request-transcription/
- Transcription runs when recording is available; result stored on session.
"""

import logging
import os
import tempfile
from urllib.parse import urlparse

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

from .recording_media import resolve_session_recording_download_url

_faster_whisper_model = None
_faster_whisper_model_key = None


def get_transcription_provider() -> str:
    """Return configured transcription backend name."""
    return (getattr(settings, "TRANSCRIPTION_PROVIDER", "openai") or "openai").lower().strip()


def is_transcription_configured() -> bool:
    """True when auto/manual transcription can run with current settings."""
    provider = get_transcription_provider()
    if provider == "faster-whisper":
        return True
    if provider in ("openai", "openai-whisper", "whisper-api", "whisper"):
        return bool(
            getattr(settings, "OPENAI_API_KEY", None)
            or getattr(settings, "TRANSCRIPTION_API_KEY", None)
        )
    return False


def get_recording_audio_url(session):
    """
    Resolve a URL that can be used to fetch the recording audio for transcription.
    Uses Twilio Media subresource (not the API resource URL stored on session).
    """
    if not session.recording_url and not session.recording_sid:
        return None
    return resolve_session_recording_download_url(session)


def _twilio_recording_auth(recording_url):
    if recording_url and "video.twilio.com/v1/Recordings" in recording_url:
        sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
        token = getattr(settings, "TWILIO_AUTH_TOKEN", None)
        if sid and token:
            return (sid, token)
    return None


def _download_recording_audio(recording_url, auth=None) -> bytes:
    import requests

    resp = requests.get(recording_url, timeout=120, auth=auth)
    resp.raise_for_status()
    return resp.content


def _recording_suffix(recording_url: str) -> str:
    path = urlparse(recording_url).path.lower()
    for ext in (".mp4", ".webm", ".mkv", ".mp3", ".wav", ".m4a", ".ogg"):
        if path.endswith(ext):
            return ext
    return ".mp4"


def run_transcription(session):
    """
    Run transcription for a completed session that has a recording.
    Sets session.transcription_status and session.transcription_text.
    """
    if session.transcription_status == "COMPLETED" and session.transcription_text:
        return True

    if session.status != "COMPLETED":
        logger.warning(
            f"Transcription requested for non-completed session {session.id}"
        )
        return False
    if not session.recording_url and not session.recording_sid:
        session.transcription_status = "FAILED"
        session.transcription_text = ""
        session.transcription_completed_at = timezone.now()
        session.save(
            update_fields=[
                "transcription_status",
                "transcription_text",
                "transcription_completed_at",
            ]
        )
        logger.info(f"Session {session.id}: no recording available for transcription")
        return False

    session.transcription_status = "PROCESSING"
    session.save(update_fields=["transcription_status"])

    if not is_transcription_configured():
        session.transcription_status = "PENDING"
        session.save(update_fields=["transcription_status"])
        logger.info(
            "Session %s: transcription set to PENDING (configure TRANSCRIPTION_PROVIDER "
            "and credentials/model settings)",
            session.id,
        )
        return False

    recording_url = get_recording_audio_url(session)
    if not recording_url and session.recording_sid:
        logger.info(
            "Session %s: recording media not ready yet (sid=%s)",
            session.id,
            session.recording_sid,
        )
        session.transcription_status = "PROCESSING"
        session.save(update_fields=["transcription_status"])
        return False

    if not recording_url:
        session.transcription_status = "FAILED"
        session.transcription_text = ""
        session.transcription_completed_at = timezone.now()
        session.save(
            update_fields=[
                "transcription_status",
                "transcription_text",
                "transcription_completed_at",
            ]
        )
        return False

    provider = get_transcription_provider()
    twilio_auth = _twilio_recording_auth(recording_url)

    try:
        if provider == "faster-whisper":
            audio_bytes = _download_recording_audio(recording_url, auth=twilio_auth)
            text = _transcribe_with_faster_whisper(
                audio_bytes, suffix=_recording_suffix(recording_url)
            )
        elif provider in ("openai", "openai-whisper", "whisper-api", "whisper"):
            api_key = getattr(settings, "OPENAI_API_KEY", None) or getattr(
                settings, "TRANSCRIPTION_API_KEY", None
            )
            if not api_key:
                raise ValueError("OPENAI_API_KEY or TRANSCRIPTION_API_KEY is required")
            text = _transcribe_with_openai_whisper(
                recording_url, api_key, auth=twilio_auth
            )
        else:
            raise ValueError(f"Unknown TRANSCRIPTION_PROVIDER: {provider}")

        if text is not None:
            session.transcription_text = text
            session.transcription_status = "COMPLETED"
            session.transcription_completed_at = timezone.now()
            session.save(
                update_fields=[
                    "transcription_text",
                    "transcription_status",
                    "transcription_completed_at",
                ]
            )
            logger.info(
                "Session %s: transcription completed via %s (%s chars)",
                session.id,
                provider,
                len(text),
            )
            return True
    except Exception as e:
        logger.exception(f"Session {session.id}: transcription failed: {e}")
        session.transcription_status = "FAILED"
        session.transcription_text = ""
        session.transcription_completed_at = timezone.now()
        session.save(
            update_fields=[
                "transcription_status",
                "transcription_text",
                "transcription_completed_at",
            ]
        )
        return False

    session.transcription_status = "PENDING"
    session.save(update_fields=["transcription_status"])
    return False


def _get_faster_whisper_model():
    """Load and cache the faster-whisper model (expensive; reuse across sessions)."""
    global _faster_whisper_model, _faster_whisper_model_key

    model_name = getattr(settings, "FASTER_WHISPER_MODEL", "base")
    device = getattr(settings, "FASTER_WHISPER_DEVICE", "cpu")
    compute_type = getattr(settings, "FASTER_WHISPER_COMPUTE_TYPE", "") or (
        "int8" if device == "cpu" else "float16"
    )
    key = (model_name, device, compute_type)
    if _faster_whisper_model is None or _faster_whisper_model_key != key:
        from faster_whisper import WhisperModel

        logger.info(
            "Loading faster-whisper model=%s device=%s compute_type=%s",
            model_name,
            device,
            compute_type,
        )
        _faster_whisper_model = WhisperModel(
            model_name, device=device, compute_type=compute_type
        )
        _faster_whisper_model_key = key
    return _faster_whisper_model


def _transcribe_with_faster_whisper(audio_bytes: bytes, suffix: str = ".mp4") -> str:
    """
    Transcribe audio locally with faster-whisper (CTranslate2).
    Requires ffmpeg on PATH for non-wav inputs.
    """
    model = _get_faster_whisper_model()
    language = getattr(settings, "FASTER_WHISPER_LANGUAGE", "") or None

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        transcribe_kwargs = {}
        if language:
            transcribe_kwargs["language"] = language

        segments, _info = model.transcribe(tmp_path, **transcribe_kwargs)
        parts = [segment.text.strip() for segment in segments if segment.text.strip()]
        return " ".join(parts).strip()
    except ImportError:
        logger.warning(
            "faster-whisper not installed; pip install faster-whisper (and ffmpeg on PATH)"
        )
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _transcribe_with_openai_whisper(recording_url, api_key, auth=None):
    """
    Call OpenAI Whisper API. Downloads recording from URL (use auth=(sid, token) for Twilio).
    """
    try:
        audio_file = _download_recording_audio(recording_url, auth=auth)

        import io

        import openai

        client = openai.OpenAI(api_key=api_key)
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=io.BytesIO(audio_file),
        )
        return transcript.text if getattr(transcript, "text", None) else str(transcript)
    except ImportError:
        logger.warning(
            "openai or requests not installed; cannot run Whisper transcription"
        )
        return None
    except Exception as e:
        logger.exception(f"Whisper transcription error: {e}")
        raise

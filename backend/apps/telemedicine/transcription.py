"""
Telemedicine session transcription.

After a session with recording, transcription can be requested to produce
text from the recording. Configure a provider (e.g. OpenAI Whisper, Deepgram)
via settings and optional env vars.

Usage:
- Request transcription: POST /api/v1/telemedicine/{id}/request-transcription/
- Transcription runs when recording is available; result stored on session.
"""
import logging
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def get_recording_audio_url(session):
    """
    Resolve a URL that can be used to fetch the recording audio for transcription.
    Twilio recording URLs may require auth; this can be extended to use
    signed URLs or a webhook-downloaded file path.
    """
    if not session.recording_url and not session.recording_sid:
        return None
    # Twilio recording URL format; may need to append .mp3 or use Media URL
    # For Group Room recordings, list via API and get media URL
    return session.recording_url or None


def run_transcription(session):
    """
    Run transcription for a completed session that has a recording.
    Sets session.transcription_status and session.transcription_text.
    Can be extended to use OpenAI Whisper, Deepgram, AWS Transcribe, etc.
    """
    from .models import TelemedicineSession

    if session.status != 'COMPLETED':
        logger.warning(f"Transcription requested for non-completed session {session.id}")
        return False
    if not session.recording_url and not session.recording_sid:
        session.transcription_status = 'FAILED'
        session.transcription_text = ''
        session.transcription_completed_at = timezone.now()
        session.save(update_fields=['transcription_status', 'transcription_text', 'transcription_completed_at'])
        logger.info(f"Session {session.id}: no recording available for transcription")
        return False

    session.transcription_status = 'PROCESSING'
    session.save(update_fields=['transcription_status'])

    # Optional: OpenAI Whisper (if OPENAI_API_KEY is set)
    api_key = getattr(settings, 'OPENAI_API_KEY', None) or getattr(settings, 'TRANSCRIPTION_API_KEY', None)
    recording_url = get_recording_audio_url(session)
    # Twilio recording URLs require Basic auth (Account SID : Auth Token)
    twilio_auth = None
    if getattr(settings, 'TWILIO_ACCOUNT_SID', None) and getattr(settings, 'TWILIO_AUTH_TOKEN', None):
        twilio_auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    if api_key and recording_url:
        try:
            text = _transcribe_with_openai_whisper(recording_url, api_key, auth=twilio_auth)
            if text is not None:
                session.transcription_text = text
                session.transcription_status = 'COMPLETED'
                session.transcription_completed_at = timezone.now()
                session.save(update_fields=['transcription_text', 'transcription_status', 'transcription_completed_at'])
                logger.info(f"Session {session.id}: transcription completed ({len(text)} chars)")
                return True
        except Exception as e:
            logger.exception(f"Session {session.id}: transcription failed: {e}")
            session.transcription_status = 'FAILED'
            session.transcription_text = ''
            session.transcription_completed_at = timezone.now()
            session.save(update_fields=['transcription_status', 'transcription_text', 'transcription_completed_at'])
            return False

    # No provider configured or URL not usable: leave as PROCESSING or mark PENDING for manual/async
    session.transcription_status = 'PENDING'
    session.save(update_fields=['transcription_status'])
    logger.info(
        f"Session {session.id}: transcription set to PENDING (configure OPENAI_API_KEY or "
        "TRANSCRIPTION_API_KEY and ensure recording URL is available for automatic transcription)"
    )
    return False


def _transcribe_with_openai_whisper(recording_url, api_key, auth=None):
    """
    Call OpenAI Whisper API. Downloads recording from URL (use auth=(sid, token) for Twilio).
    """
    try:
        import requests
        # Download recording (Twilio URLs need Basic auth: Account SID, Auth Token)
        resp = requests.get(recording_url, timeout=60, auth=auth)
        resp.raise_for_status()
        audio_file = resp.content

        import openai
        client = openai.OpenAI(api_key=api_key)
        # Whisper accepts file-like object or path
        import io
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=io.BytesIO(audio_file),
        )
        return transcript.text if getattr(transcript, 'text', None) else str(transcript)
    except ImportError:
        logger.warning("openai or requests not installed; cannot run Whisper transcription")
        return None
    except Exception as e:
        logger.exception(f"Whisper transcription error: {e}")
        raise

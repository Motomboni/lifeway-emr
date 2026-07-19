"""
Celery tasks for automatic telemedicine transcription after sessions end.
"""

import logging
import time

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.telemedicine.transcription import is_transcription_configured

logger = logging.getLogger(__name__)

MAX_TRANSCRIPTION_ATTEMPTS = 12
RETRY_DELAY_SECONDS = 30


def _should_auto_transcribe() -> bool:
    if not getattr(settings, "TELEMEDICINE_AUTO_TRANSCRIPTION", True):
        return False
    return is_transcription_configured()


def schedule_auto_transcription(session_id: int) -> None:
    """
    Queue automatic transcription when a recorded session ends.
    Uses Celery when available; falls back to a background thread in dev.
    """
    if not _should_auto_transcribe():
        logger.info(
            "Auto-transcription skipped for session %s (disabled or no API key)",
            session_id,
        )
        return

    try:
        auto_transcribe_session.delay(session_id, attempt=0)
        return
    except Exception as exc:
        logger.info(
            "Celery unavailable for session %s transcription (%s); using thread fallback",
            session_id,
            exc,
        )

    import threading

    threading.Thread(
        target=_run_transcription_with_retries,
        args=(session_id,),
        daemon=True,
    ).start()


def _run_transcription_with_retries(session_id: int) -> None:
    """Synchronous retry loop (dev fallback when Celery worker is not running)."""
    from apps.telemedicine.models import TelemedicineSession
    from apps.telemedicine.transcription import run_transcription
    from apps.telemedicine.video_providers import refresh_session_recording

    for attempt in range(MAX_TRANSCRIPTION_ATTEMPTS):
        try:
            session = TelemedicineSession.objects.get(pk=session_id)
        except TelemedicineSession.DoesNotExist:
            return

        if session.transcription_status == "COMPLETED" and session.transcription_text:
            return

        if session.recording_enabled and not session.recording_sid:
            refresh_session_recording(session)

        if run_transcription(session):
            return

        session.refresh_from_db()
        if session.transcription_status == "FAILED":
            return

        if attempt < MAX_TRANSCRIPTION_ATTEMPTS - 1:
            time.sleep(RETRY_DELAY_SECONDS)


@shared_task(name="apps.telemedicine.tasks.auto_transcribe_session")
def auto_transcribe_session(session_id: int, attempt: int = 0):
    """
    Transcribe a completed telemedicine session recording (OpenAI Whisper or faster-whisper).
    Retries while Twilio media is still processing.
    """
    from apps.telemedicine.models import TelemedicineSession
    from apps.telemedicine.transcription import run_transcription
    from apps.telemedicine.video_providers import refresh_session_recording

    try:
        session = TelemedicineSession.objects.get(pk=session_id)
    except TelemedicineSession.DoesNotExist:
        logger.warning("Auto-transcribe: session %s not found", session_id)
        return {"status": "missing"}

    if session.transcription_status == "COMPLETED" and session.transcription_text:
        return {"status": "already_done"}

    if not session.recording_enabled:
        return {"status": "recording_disabled"}

    if session.transcription_status in ("", "FAILED"):
        session.transcription_requested_at = timezone.now()
        session.transcription_status = "PENDING"
        session.save(update_fields=["transcription_requested_at", "transcription_status"])

    if not session.recording_sid:
        refresh_session_recording(session)
        session.refresh_from_db()

    if run_transcription(session):
        return {"status": "completed", "session_id": session_id}

    session.refresh_from_db()
    if session.transcription_status == "FAILED":
        return {"status": "failed", "session_id": session_id}

    if attempt + 1 < MAX_TRANSCRIPTION_ATTEMPTS:
        auto_transcribe_session.apply_async(
            args=[session_id],
            kwargs={"attempt": attempt + 1},
            countdown=RETRY_DELAY_SECONDS,
        )
        return {"status": "retry_scheduled", "attempt": attempt + 1}

    session.transcription_status = "FAILED"
    session.transcription_completed_at = timezone.now()
    session.save(update_fields=["transcription_status", "transcription_completed_at"])
    return {"status": "exhausted_retries", "session_id": session_id}

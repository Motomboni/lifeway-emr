"""Tests for telemedicine transcription providers."""

from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from apps.telemedicine.transcription import (
    get_transcription_provider,
    is_transcription_configured,
    run_transcription,
    _transcribe_with_faster_whisper,
)


@pytest.mark.parametrize(
    "provider,openai_key,expected",
    [
        ("faster-whisper", "", True),
        ("openai", "sk-test", True),
        ("openai", "", False),
    ],
)
def test_is_transcription_configured(provider, openai_key, expected):
    with override_settings(
        TRANSCRIPTION_PROVIDER=provider,
        OPENAI_API_KEY=openai_key,
        TRANSCRIPTION_API_KEY="",
    ):
        assert is_transcription_configured() is expected


def test_get_transcription_provider_normalizes_value():
    with override_settings(TRANSCRIPTION_PROVIDER=" Faster-Whisper "):
        assert get_transcription_provider() == "faster-whisper"


@pytest.mark.django_db
@override_settings(TRANSCRIPTION_PROVIDER="faster-whisper")
def test_run_transcription_uses_faster_whisper():
    session = MagicMock()
    session.id = 42
    session.transcription_status = "PENDING"
    session.transcription_text = ""
    session.status = "COMPLETED"
    session.recording_url = "https://video.twilio.com/v1/Recordings/RE123/Media"
    session.recording_sid = "RE123"
    session.transcription_completed_at = None

    with patch(
        "apps.telemedicine.transcription.get_recording_audio_url",
        return_value="https://video.twilio.com/v1/Recordings/RE123/Media",
    ), patch(
        "apps.telemedicine.transcription._download_recording_audio",
        return_value=b"fake-audio",
    ), patch(
        "apps.telemedicine.transcription._transcribe_with_faster_whisper",
        return_value="Patient reports mild headache.",
    ) as mock_fw:
        assert run_transcription(session) is True

    assert session.transcription_status == "COMPLETED"
    assert session.transcription_text == "Patient reports mild headache."
    session.save.assert_called()
    mock_fw.assert_called_once()


@override_settings(
    FASTER_WHISPER_MODEL="tiny",
    FASTER_WHISPER_DEVICE="cpu",
    FASTER_WHISPER_COMPUTE_TYPE="int8",
)
def test_transcribe_with_faster_whisper_joins_segments():
    mock_segment_a = MagicMock(text=" Hello ")
    mock_segment_b = MagicMock(text=" world ")
    mock_model = MagicMock()
    mock_model.transcribe.return_value = ([mock_segment_a, mock_segment_b], MagicMock())

    with patch(
        "apps.telemedicine.transcription._get_faster_whisper_model",
        return_value=mock_model,
    ):
        text = _transcribe_with_faster_whisper(b"audio-bytes", suffix=".wav")

    assert text == "Hello world"
    mock_model.transcribe.assert_called_once()

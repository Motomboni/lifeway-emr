"""Tests for telemedicine video provider routing."""

from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.telemedicine.video_providers import (
    PROVIDER_LIVEKIT,
    PROVIDER_TWILIO,
    create_video_room,
    generate_video_access_token,
    get_active_video_provider,
    get_public_video_config,
    is_video_provider_configured,
)


@override_settings(TELEMEDICINE_VIDEO_PROVIDER="livekit")
def test_get_active_video_provider_livekit():
    assert get_active_video_provider() == PROVIDER_LIVEKIT


@override_settings(
    TELEMEDICINE_VIDEO_PROVIDER="livekit",
    LIVEKIT_URL="wss://test.livekit.cloud",
    LIVEKIT_API_KEY="key",
    LIVEKIT_API_SECRET="secret",
)
def test_livekit_provider_configured():
    assert is_video_provider_configured(PROVIDER_LIVEKIT) is True


@override_settings(
    TELEMEDICINE_VIDEO_PROVIDER="livekit",
    LIVEKIT_URL="wss://test.livekit.cloud",
    LIVEKIT_API_KEY="key",
    LIVEKIT_API_SECRET="secret",
)
def test_public_video_config_includes_livekit_url():
    config = get_public_video_config(PROVIDER_LIVEKIT)
    assert config["video_provider"] == PROVIDER_LIVEKIT
    assert config["livekit_url"] == "wss://test.livekit.cloud"


@override_settings(TELEMEDICINE_VIDEO_PROVIDER="livekit")
@patch("apps.telemedicine.livekit_utils.create_livekit_room")
def test_create_video_room_routes_to_livekit(mock_create):
    mock_create.return_value = {
        "room_sid": "lk-room-1",
        "room_name": "visit-1-abc",
        "status": "open",
    }
    info = create_video_room("visit-1-abc")
    assert info["video_provider"] == PROVIDER_LIVEKIT
    mock_create.assert_called_once()


@override_settings(TELEMEDICINE_VIDEO_PROVIDER="twilio")
@patch("apps.telemedicine.utils.create_twilio_room")
def test_create_video_room_routes_to_twilio(mock_create):
    mock_create.return_value = {
        "room_sid": "RM123",
        "room_name": "visit-1-abc",
        "status": "in-progress",
    }
    info = create_video_room("visit-1-abc")
    assert info["video_provider"] == PROVIDER_TWILIO
    mock_create.assert_called_once()


@override_settings(
    TELEMEDICINE_VIDEO_PROVIDER="livekit",
    LIVEKIT_URL="wss://test.livekit.cloud",
    LIVEKIT_API_KEY="key",
    LIVEKIT_API_SECRET="secret",
)
@patch("apps.telemedicine.livekit_utils.generate_livekit_access_token")
def test_generate_token_routes_to_livekit(mock_token, doctor_user):
    mock_token.return_value = "jwt-livekit"
    token = generate_video_access_token(
        doctor_user, room_name="room-a", provider=PROVIDER_LIVEKIT
    )
    assert token == "jwt-livekit"
    mock_token.assert_called_once()

"""Tests for Orthanc PACS integration."""

from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from rest_framework.exceptions import ValidationError

from apps.radiology.orthanc_service import OrthancService


@pytest.mark.django_db
class TestOrthancService:
    @override_settings(ORTHANC_URL="")
    def test_is_enabled_false_when_unconfigured(self):
        assert OrthancService.is_enabled() is False

    @override_settings(ORTHANC_URL="http://orthanc:8042")
    def test_is_enabled_true_when_configured(self):
        assert OrthancService.is_enabled() is True

    @override_settings(ORTHANC_URL="http://orthanc:8042", ORTHANC_USERNAME="orthanc", ORTHANC_PASSWORD="orthanc")
    @patch("apps.radiology.orthanc_service.requests.request")
    def test_stow_instance_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "ID": "abc123",
            "ParentStudy": "study-id",
            "ParentSeries": "series-id",
            "Path": "/instances/abc123",
            "Status": "Success",
        }
        mock_request.return_value = mock_response

        result = OrthancService.stow_instance(b"\x00\x01DICOM")

        assert result["ID"] == "abc123"
        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["auth"] == ("orthanc", "orthanc")
        assert call_kwargs["headers"]["Content-Type"] == "application/dicom"

    @override_settings(ORTHANC_URL="http://orthanc:8042")
    @patch("apps.radiology.orthanc_service.requests.request")
    def test_stow_instance_raises_on_failure(self, mock_request):
        import requests

        mock_request.side_effect = requests.ConnectionError("connection refused")

        with pytest.raises(ValidationError, match="Orthanc"):
            OrthancService.stow_instance(b"\x00\x01DICOM")

    @override_settings(ORTHANC_URL="")
    def test_stow_skipped_when_disabled(self):
        assert OrthancService.stow_instance(b"data") == {}

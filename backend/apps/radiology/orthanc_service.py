"""
Orthanc PACS integration — STOW-RS via REST and DICOMweb viewer support.

When ORTHANC_URL is configured, DICOM instances are stored in Orthanc on ingest
so OHIF (Orthanc plugin) can load studies via DICOMweb.
"""

from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)


class OrthancService:
    """Thin client for Orthanc REST API (instance upload, study lookup)."""

    @staticmethod
    def is_enabled() -> bool:
        return bool(getattr(settings, "ORTHANC_URL", None))

    @staticmethod
    def _base_url() -> str:
        return str(settings.ORTHANC_URL).rstrip("/")

    @staticmethod
    def _auth() -> tuple[str, str] | None:
        username = getattr(settings, "ORTHANC_USERNAME", "") or ""
        password = getattr(settings, "ORTHANC_PASSWORD", "") or ""
        if username:
            return (username, password)
        return None

    @staticmethod
    def _request(
        method: str,
        path: str,
        *,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
        timeout: int = 120,
    ) -> requests.Response:
        url = f"{OrthancService._base_url()}{path}"
        return requests.request(
            method,
            url,
            data=data,
            headers=headers,
            auth=OrthancService._auth(),
            timeout=timeout,
        )

    @staticmethod
    def stow_instance(dicom_bytes: bytes) -> dict[str, Any]:
        """
        Upload one DICOM instance to Orthanc (POST /instances).

        Returns Orthanc JSON (ID, ParentStudy, ParentSeries, Path, Status).
        """
        if not OrthancService.is_enabled():
            return {}

        if not dicom_bytes:
            raise ValidationError("Empty DICOM payload for Orthanc STOW.")

        try:
            response = OrthancService._request(
                "POST",
                "/instances",
                data=dicom_bytes,
                headers={"Content-Type": "application/dicom"},
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.exception("Orthanc STOW failed")
            raise ValidationError(
                "Failed to store DICOM in Orthanc PACS. Check ORTHANC_URL and credentials."
            ) from exc

        payload = response.json()
        logger.info(
            "Orthanc STOW ok instance=%s study=%s",
            payload.get("ID"),
            payload.get("ParentStudy"),
        )
        return payload

    @staticmethod
    def find_study_id_by_uid(study_instance_uid: str) -> str | None:
        """Resolve Orthanc internal study ID from DICOM StudyInstanceUID."""
        if not OrthancService.is_enabled() or not study_instance_uid:
            return None

        try:
            response = OrthancService._request(
                "POST",
                "/tools/find",
                data=(
                    '{"Level":"Study","Query":{"StudyInstanceUID":"'
                    + study_instance_uid.replace('"', "")
                    + '"},"Expand":false}'
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            response.raise_for_status()
            ids = response.json()
            return ids[0] if ids else None
        except requests.RequestException:
            logger.warning(
                "Could not resolve Orthanc study for UID %s", study_instance_uid
            )
            return None

    @staticmethod
    def ping() -> bool:
        """Return True if Orthanc /system responds."""
        if not OrthancService.is_enabled():
            return False
        try:
            response = OrthancService._request("GET", "/system", timeout=5)
            return response.ok
        except requests.RequestException:
            return False

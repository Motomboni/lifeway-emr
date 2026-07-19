"""
DICOM ingest — parse tags with pydicom and store via PACS-lite.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from django.utils import timezone
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)


def _require_pydicom():
    try:
        import pydicom
        from pydicom.errors import InvalidDicomError

        return pydicom, InvalidDicomError
    except ImportError as exc:
        raise ValidationError(
            "DICOM support is not installed on the server (missing pydicom)."
        ) from exc


def parse_dicom_bytes(content: bytes) -> dict[str, Any]:
    """Extract UIDs and metadata from a DICOM file."""
    pydicom, InvalidDicomError = _require_pydicom()
    from pydicom.dataset import FileDataset

    try:
        from io import BytesIO

        ds: FileDataset = pydicom.dcmread(BytesIO(content), force=True)
    except InvalidDicomError as exc:
        raise ValidationError("Invalid DICOM file.") from exc

    def _get(tag: str, default=None):
        return getattr(ds, tag, default) if hasattr(ds, tag) else default

    study_date = _get("StudyDate")
    parsed_study_date = None
    if study_date and len(str(study_date)) >= 8:
        s = str(study_date)
        try:
            from datetime import date

            parsed_study_date = date(int(s[:4]), int(s[4:6]), int(s[6:8]))
        except ValueError:
            parsed_study_date = None

    return {
        "study_uid": str(_get("StudyInstanceUID") or ""),
        "series_uid": str(_get("SeriesInstanceUID") or ""),
        "sop_instance_uid": str(_get("SOPInstanceUID") or ""),
        "study_description": str(_get("StudyDescription") or "")[:255],
        "series_description": str(_get("SeriesDescription") or "")[:255],
        "modality": str(_get("Modality") or "")[:10],
        "series_number": int(_get("SeriesNumber") or 0) or None,
        "instance_number": int(_get("InstanceNumber") or 0) or None,
        "study_date": parsed_study_date,
        "patient_name": str(_get("PatientName") or "")[:255],
        "patient_id": str(_get("PatientID") or "")[:100],
        "transfer_syntax": str(getattr(ds.file_meta, "TransferSyntaxUID", "") or ""),
    }


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def ingest_dicom_for_request(radiology_request, uploaded_file, user):
    """
    Parse and store one DICOM instance for a RadiologyRequest.
    Returns dict with study_id, image_uid, image_count.
    """
    from .pacs_lite_service import PACSLiteService

    content = uploaded_file.read()
    if not content:
        raise ValidationError("Empty DICOM file.")

    meta = parse_dicom_bytes(content)
    if not meta["study_uid"] or not meta["series_uid"] or not meta["sop_instance_uid"]:
        raise ValidationError("DICOM file is missing required UIDs.")

    checksum = sha256_hex(content)
    filename = getattr(uploaded_file, "name", "instance.dcm") or "instance.dcm"
    mime_type = getattr(uploaded_file, "content_type", None) or "application/dicom"

    image = PACSLiteService.ingest_dicom_instance(
        radiology_request=radiology_request,
        file_content=content,
        filename=filename,
        mime_type=mime_type,
        checksum=checksum,
        meta=meta,
        uploaded_by=user,
    )

    radiology_request.refresh_from_db()
    study = radiology_request.pacs_study
    image_count = (
        sum(s.images.count() for s in study.series.all()) if study else 1
    )
    radiology_request.image_count = image_count
    radiology_request.image_metadata = {
        **(radiology_request.image_metadata or {}),
        "modality": meta.get("modality") or radiology_request.image_metadata.get(
            "modality"
        ),
        "study_uid": meta["study_uid"],
        "last_upload_at": timezone.now().isoformat(),
    }
    radiology_request.save(
        update_fields=["image_count", "image_metadata", "updated_at"]
    )

    return {
        "study_id": study.id if study else None,
        "study_uid": meta["study_uid"],
        "image_uid": image.image_uid,
        "image_count": image_count,
        "modality": meta.get("modality"),
    }

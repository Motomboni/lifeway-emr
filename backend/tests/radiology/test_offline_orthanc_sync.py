"""Tests for Orthanc STOW during offline radiology sync."""

import hashlib
from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.radiology.models import RadiologyOrder
from apps.radiology.offline_image_models import OfflineImageMetadata
from apps.radiology.offline_sync_service import OfflineImageSyncService
from apps.radiology.pacs_lite_models import RadiologyImage


@pytest.mark.django_db
class TestOfflineRadiologyOrthanc:
    @override_settings(ORTHANC_URL="http://orthanc:8042")
    @patch("apps.radiology.orthanc_service.OrthancService.stow_instance")
    def test_offline_upload_stows_to_orthanc(
        self,
        mock_stow,
        open_visit_with_payment,
        consultation,
        doctor_user,
    ):
        mock_stow.return_value = {
            "ID": "orthanc-inst-1",
            "ParentStudy": "study-1",
            "ParentSeries": "series-1",
        }

        order = RadiologyOrder.objects.create(
            visit=open_visit_with_payment,
            ordered_by=doctor_user,
            imaging_type="XRAY",
            body_part="Chest",
            clinical_indication="Cough",
            status="ORDERED",
        )

        dicom_bytes = b"\x00\x01DICOM test content for orthanc"
        checksum = hashlib.sha256(dicom_bytes).hexdigest()

        metadata = OfflineImageMetadata.objects.create(
            radiology_order=order,
            filename="scan.dcm",
            mime_type="application/dicom",
            file_size=len(dicom_bytes),
            checksum=checksum,
            image_metadata={
                "study_uid": "1.2.3.4",
                "series_uid": "1.2.3.4.5",
                "sop_instance_uid": "1.2.3.4.5.6",
            },
            status="METADATA_UPLOADED",
        )

        image = OfflineImageSyncService.upload_binary(
            image_uuid=str(metadata.image_uuid),
            file_content=dicom_bytes,
            user=doctor_user,
        )

        mock_stow.assert_called_once()
        stored = RadiologyImage.objects.get(id=image.id)
        assert stored.image_metadata.get("orthanc", {}).get("instance_id") == "orthanc-inst-1"

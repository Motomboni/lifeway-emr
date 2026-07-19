"""
PACS-lite Viewer Views - OHIF Viewer Integration

Per EMR Context Document v2 (LOCKED):
- PACS-lite DOES: Expose viewer URLs, Enforce read-only access
- Viewer Strategy: OHIF Viewer (recommended) or lightweight DICOM viewer
- Access controlled via signed URLs
"""

import logging

from django.conf import settings
from django.db.models import Q
from django.http import FileResponse, Http404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.tenant import filter_by_related_organization

from .pacs_lite_models import RadiologyImage, RadiologyStudy
from .pacs_lite_service import PACSLiteService
from .permissions import CanViewRadiologyRequest

logger = logging.getLogger(__name__)


class RadiologyStudyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing radiology studies (read-only).

    Per PACS-lite: Read-only access enforced.
    """

    queryset = RadiologyStudy.objects.all()
    permission_classes = [IsAuthenticated, CanViewRadiologyRequest]

    def get_queryset(self):
        """Filter by radiology order or request if provided."""
        queryset = super().get_queryset()
        org = getattr(self.request, "organization", None)
        if org and not getattr(self.request.user, "is_superuser", False):
            queryset = queryset.filter(
                Q(radiology_order__visit__organization=org)
                | Q(radiology_request__visit__organization=org)
            )
        radiology_order_id = self.request.query_params.get("radiology_order_id")
        radiology_request_id = self.request.query_params.get("radiology_request_id")
        if radiology_order_id:
            queryset = queryset.filter(radiology_order_id=radiology_order_id)
        if radiology_request_id:
            queryset = queryset.filter(radiology_request_id=radiology_request_id)
        return queryset.select_related(
            "radiology_order",
            "radiology_order__visit",
            "radiology_order__visit__patient",
            "radiology_request",
            "radiology_request__visit",
            "radiology_request__visit__patient",
        )

    @action(detail=True, methods=["get"], url_path="viewer-url")
    def viewer_url(self, request, pk=None):
        """
        Generate signed viewer URL for OHIF Viewer.

        Per PACS-lite: Access controlled via signed URLs.

        Returns:
            Viewer URL with signed token
        """
        study = self.get_object()

        visit = None
        if study.radiology_request_id:
            visit = study.radiology_request.visit
        elif study.radiology_order_id:
            visit = study.radiology_order.visit
        user = request.user

        # Generate viewer URL
        viewer_url = PACSLiteService.generate_viewer_url(
            study_uid=study.study_uid,
            user=user,
            expires_in=3600,  # 1 hour
        )

        return Response(
            {
                "viewer_url": viewer_url,
                "study_uid": study.study_uid,
                "expires_in": 3600,
                "orthanc_enabled": bool(getattr(settings, "ORTHANC_URL", None)),
            }
        )

    @action(detail=True, methods=["get"], url_path="images")
    def images(self, request, pk=None):
        """
        Get all images for a study (grouped by series).

        Per PACS-lite: Group by Study/Series.
        """
        study = self.get_object()

        # Get images grouped by series
        images = PACSLiteService.get_study_images(study.study_uid)

        # Group by series
        series_dict = {}
        for image in images:
            series_uid = image.series.series_uid
            if series_uid not in series_dict:
                series_dict[series_uid] = {
                    "series_uid": series_uid,
                    "series_description": image.series.series_description,
                    "series_number": image.series.series_number,
                    "modality": image.series.modality,
                    "images": [],
                }

            # Generate signed image URL
            image_url = PACSLiteService.generate_image_url(
                image=image,
                user=request.user,
                expires_in=3600,
            )

            series_dict[series_uid]["images"].append(
                {
                    "image_uid": image.image_uid,
                    "filename": image.filename,
                    "file_size": image.file_size,
                    "mime_type": image.mime_type,
                    "instance_number": image.instance_number,
                    "image_url": image_url,
                }
            )

        return Response(
            {
                "study_uid": study.study_uid,
                "study_description": study.study_description,
                "series": list(series_dict.values()),
            }
        )


class RadiologyImageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing individual radiology images (read-only).

    Per PACS-lite: Read-only access enforced.
    """

    queryset = RadiologyImage.objects.all()
    permission_classes = [IsAuthenticated, CanViewRadiologyRequest]

    def get_queryset(self):
        """Filter by study or series if provided."""
        queryset = filter_by_related_organization(
            super().get_queryset(),
            self.request,
            "series__study__radiology_order__visit__organization",
        )
        study_uid = self.request.query_params.get("study_uid")
        series_uid = self.request.query_params.get("series_uid")

        if study_uid:
            queryset = queryset.filter(series__study__study_uid=study_uid)
        if series_uid:
            queryset = queryset.filter(series__series_uid=series_uid)

        return queryset.select_related("series", "series__study", "uploaded_by")

    @action(detail=True, methods=["get"], url_path="url")
    def image_url(self, request, pk=None):
        """
        Generate signed URL for individual image access.

        Per PACS-lite: Read-only access enforced.
        """
        image = self.get_object()

        # Generate signed image URL
        image_url = PACSLiteService.generate_image_url(
            image=image,
            user=request.user,
            expires_in=3600,  # 1 hour
        )

        return Response(
            {
                "image_url": image_url,
                "image_uid": image.image_uid,
                "filename": image.filename,
                "expires_in": 3600,
            }
        )

    @action(detail=True, methods=["get"], url_path="file")
    def download_file(self, request, pk=None):
        """Stream stored DICOM/JPEG file (authenticated, read-only)."""
        image = self.get_object()
        if not image.file_key:
            raise Http404("Image file not found.")
        storage = PACSLiteService.get_storage_backend()
        if not storage.exists(image.file_key):
            raise Http404("Image file not found in storage.")
        handle = storage.open(image.file_key, "rb")
        response = FileResponse(handle, content_type=image.mime_type or "application/dicom")
        response["Content-Disposition"] = f'inline; filename="{image.filename or "study.dcm"}"'
        return response

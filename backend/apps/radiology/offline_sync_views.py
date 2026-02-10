"""
Views for Offline Image Sync API.

Per EMR Context Document v2 (LOCKED):
- Metadata syncs before binaries
- No image is deleted locally until server ACK
- Images are immutable
- No overwrite allowed
- Checksums validated server-side
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError
from django.db import transaction

from .offline_image_models import OfflineImageMetadata
from .pacs_lite_models import RadiologyImage
from .offline_sync_service import OfflineImageSyncService
from .offline_sync_serializers import (
    OfflineImageMetadataSerializer,
    OfflineImageMetadataUploadSerializer,
    OfflineImageBinaryUploadSerializer,
    RadiologyImageSerializer,
    OfflineImageACKSerializer,
)
from .permissions import CanUpdateRadiologyReport

logger = logging.getLogger(__name__)


class OfflineImageMetadataViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing offline image metadata.
    
    Per EMR Context Document v2:
    - Metadata syncs before binaries
    - No image is deleted locally until server ACK
    """
    queryset = OfflineImageMetadata.objects.all()
    serializer_class = OfflineImageMetadataSerializer
    permission_classes = [IsAuthenticated, CanUpdateRadiologyReport]
    
    def get_queryset(self):
        """Filter by radiology order if provided."""
        queryset = super().get_queryset()
        radiology_order_id = self.request.query_params.get('radiology_order_id')
        if radiology_order_id:
            queryset = queryset.filter(radiology_order_id=radiology_order_id)
        return queryset.select_related('radiology_order')
    
    @action(detail=False, methods=['post'], url_path='upload-metadata')
    def upload_metadata(self, request):
        """
        Upload metadata for an offline image (FIRST STEP).
        
        Per EMR Context Document v2: "Metadata syncs before binaries"
        
        Flow:
        1. Client queues metadata locally
        2. Client uploads metadata to this endpoint
        3. Server validates and stores metadata
        4. Client can now upload binary
        """
        serializer = OfflineImageMetadataUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            metadata = OfflineImageSyncService.upload_metadata(
                image_uuid=serializer.validated_data['image_uuid'],
                radiology_order_id=serializer.validated_data['radiology_order_id'],
                filename=serializer.validated_data['filename'],
                file_size=serializer.validated_data['file_size'],
                mime_type=serializer.validated_data['mime_type'],
                checksum=serializer.validated_data['checksum'],
                image_metadata=serializer.validated_data.get('image_metadata', {}),
                user=request.user,
            )
            
            response_serializer = OfflineImageMetadataSerializer(metadata)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            logger.error(f"Metadata upload failed: {e}")
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'], url_path='upload-binary')
    def upload_binary(self, request):
        """
        Upload binary for an offline image (SECOND STEP).
        
        Per EMR Context Document v2: "Binaries uploaded after metadata"
        
        Flow:
        1. Metadata must be uploaded first
        2. Client uploads binary to this endpoint
        3. Server validates checksum
        4. Server creates RadiologyImage
        5. Client can request ACK
        """
        serializer = OfflineImageBinaryUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        image_uuid = serializer.validated_data['image_uuid']
        file_obj = serializer.validated_data['file']
        
        try:
            # Read file content
            file_content = file_obj.read()
            
            # Upload binary
            image = OfflineImageSyncService.upload_binary(
                image_uuid=image_uuid,
                file_content=file_content,
                user=request.user,
            )
            
            # Image is already saved by the service (stored in PACS-lite storage)
            # No need to save file_obj separately
            
            response_serializer = RadiologyImageSerializer(image)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            logger.error(f"Binary upload failed: {e}")
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Binary upload error: {e}", exc_info=True)
            return Response(
                {'detail': f"Upload failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='acknowledge')
    def acknowledge(self, request):
        """
        Acknowledge successful upload (THIRD STEP).
        
        Per EMR Context Document v2: "Local copy deleted ONLY after ACK"
        
        Flow:
        1. Binary must be uploaded and validated
        2. Client requests ACK
        3. Server marks metadata as ACK_RECEIVED
        4. Client can safely delete local copy
        """
        serializer = OfflineImageACKSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        image_uuid = serializer.validated_data['image_uuid']
        
        try:
            metadata = OfflineImageSyncService.acknowledge_upload(image_uuid=image_uuid)
            
            response_serializer = OfflineImageMetadataSerializer(metadata)
            return Response(
                response_serializer.data,
                status=status.HTTP_200_OK
            )
        except ValidationError as e:
            logger.error(f"ACK failed: {e}")
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'], url_path='pending')
    def pending_uploads(self, request):
        """Get list of pending uploads (for client-side sync)."""
        radiology_order_id = request.query_params.get('radiology_order_id')
        if radiology_order_id:
            try:
                radiology_order_id = int(radiology_order_id)
            except ValueError:
                return Response(
                    {'detail': 'Invalid radiology_order_id'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        pending = OfflineImageSyncService.get_pending_uploads(
            radiology_order_id=radiology_order_id
        )
        
        serializer = OfflineImageMetadataSerializer(pending, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='failed')
    def failed_uploads(self, request):
        """Get list of failed uploads (for manual intervention)."""
        radiology_order_id = request.query_params.get('radiology_order_id')
        if radiology_order_id:
            try:
                radiology_order_id = int(radiology_order_id)
            except ValueError:
                return Response(
                    {'detail': 'Invalid radiology_order_id'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        failed = OfflineImageSyncService.get_failed_uploads(
            radiology_order_id=radiology_order_id
        )
        
        serializer = OfflineImageMetadataSerializer(failed, many=True)
        return Response(serializer.data)


class RadiologyImageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing radiology images (read-only).
    
    Per EMR Context Document v2: "Images are immutable"
    """
    queryset = RadiologyImage.objects.all()
    serializer_class = RadiologyImageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter by study or series if provided."""
        queryset = super().get_queryset()
        study_uid = self.request.query_params.get('study_uid')
        series_uid = self.request.query_params.get('series_uid')
        radiology_order_id = self.request.query_params.get('radiology_order_id')
        
        if study_uid:
            queryset = queryset.filter(series__study__study_uid=study_uid)
        if series_uid:
            queryset = queryset.filter(series__series_uid=series_uid)
        if radiology_order_id:
            queryset = queryset.filter(series__study__radiology_order_id=radiology_order_id)
        
        return queryset.select_related('series', 'series__study', 'series__study__radiology_order', 'uploaded_by', 'offline_metadata')


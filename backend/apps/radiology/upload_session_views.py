"""
API views for Image Upload Sessions.

Provides idempotent endpoints for offline-first image uploads.
"""
import logging
import hashlib
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.core.files.uploadedfile import InMemoryUploadedFile

from .upload_session_models import ImageUploadSession, ImageUploadItem
from .offline_image_models import OfflineImageMetadata
from .offline_sync_service import OfflineImageSyncService
from .offline_sync_serializers import OfflineImageMetadataSerializer
from .models import RadiologyOrder
from .upload_session_serializers import (
    ImageUploadSessionSerializer,
    ImageUploadSessionCreateSerializer,
    ImageUploadItemSerializer,
    BinaryUploadSerializer,
)

logger = logging.getLogger(__name__)


class ImageUploadSessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Image Upload Sessions.
    
    Provides idempotent endpoints for creating and managing upload sessions.
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get upload sessions for the current user or a specific radiology order."""
        queryset = ImageUploadSession.objects.select_related(
            'radiology_order',
            'created_by'
        ).prefetch_related('upload_items__metadata')
        
        radiology_order_id = self.request.query_params.get('radiology_order_id')
        if radiology_order_id:
            queryset = queryset.filter(radiology_order_id=radiology_order_id)
        
        # Filter by current user's sessions (or all if admin)
        if not self.request.user.is_staff:
            queryset = queryset.filter(created_by=self.request.user)
        
        return queryset
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return ImageUploadSessionCreateSerializer
        return ImageUploadSessionSerializer
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Create a new upload session (idempotent).
        
        If a session with the same session_uuid exists, return it.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        session_uuid = serializer.validated_data['session_uuid']
        
        # Check for existing session (idempotency)
        existing_session = ImageUploadSession.objects.filter(
            session_uuid=session_uuid
        ).first()
        
        if existing_session:
            logger.info(f"Upload session {session_uuid} already exists, returning existing")
            return Response(
                ImageUploadSessionSerializer(existing_session).data,
                status=status.HTTP_200_OK
            )
        
        # Create new session
        session = serializer.save(created_by=request.user)
        logger.info(f"Created new upload session {session_uuid} for order {session.radiology_order_id}")
        
        return Response(
            ImageUploadSessionSerializer(session).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'], url_path='upload-metadata')
    @transaction.atomic
    def upload_metadata(self, request, pk=None):
        """
        Upload metadata for an image (idempotent).
        
        This is the FIRST step in the upload process.
        Metadata is uploaded before binaries to ensure we have a record
        even if the binary upload fails.
        """
        session = self.get_object()
        
        # Validate session status
        if session.status == 'SYNCED':
            return Response(
                {'detail': 'Session already synced. Cannot upload more images.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Mark session as started
        if session.status == 'QUEUED':
            session.mark_started()
        
        # Extract metadata from request
        image_uuid = request.data.get('image_uuid')
        filename = request.data.get('filename')
        file_size = int(request.data.get('file_size', 0))
        mime_type = request.data.get('mime_type', 'image/jpeg')
        checksum = request.data.get('checksum')
        image_metadata = request.data.get('image_metadata', {})
        sequence_number = int(request.data.get('sequence_number', 0))
        
        if not all([image_uuid, filename, checksum]):
            return Response(
                {'detail': 'Missing required fields: image_uuid, filename, checksum'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate checksum format
        if len(checksum) != 64:
            return Response(
                {'detail': 'Checksum must be SHA-256 (64 hex characters)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Check if metadata already uploaded (idempotency)
            existing_metadata = OfflineImageMetadata.objects.filter(
                image_uuid=image_uuid
            ).first()
            
            if existing_metadata:
                if existing_metadata.status == 'ACK_RECEIVED':
                    return Response(
                        {
                            'detail': 'Image already uploaded and ACK received',
                            'metadata': OfflineImageMetadataSerializer(existing_metadata).data
                        },
                        status=status.HTTP_200_OK
                    )
                elif existing_metadata.status in ['METADATA_UPLOADED', 'BINARY_UPLOADED']:
                    # Update existing metadata (retry)
                    existing_metadata.filename = filename
                    existing_metadata.file_size = file_size
                    existing_metadata.mime_type = mime_type
                    existing_metadata.checksum = checksum
                    existing_metadata.image_metadata = image_metadata
                    existing_metadata.save()
                    metadata = existing_metadata
                else:
                    metadata = existing_metadata
            else:
                # Create new metadata
                metadata = OfflineImageSyncService.upload_metadata(
                    image_uuid=image_uuid,
                    radiology_order_id=session.radiology_order_id,
                    filename=filename,
                    file_size=file_size,
                    mime_type=mime_type,
                    checksum=checksum,
                    image_metadata=image_metadata,
                    user=request.user,
                )
            
            # Create or update upload item
            upload_item, created = ImageUploadItem.objects.get_or_create(
                session=session,
                sequence_number=sequence_number,
                defaults={
                    'metadata': metadata,
                    'upload_status': 'METADATA_UPLOADED' if metadata.status == 'METADATA_UPLOADED' else 'PENDING',
                }
            )
            
            if not created:
                upload_item.metadata = metadata
                upload_item.update_status('METADATA_UPLOADED')
            
            # Update session total if needed
            if sequence_number >= session.total_images:
                session.total_images = sequence_number + 1
                session.save(update_fields=['total_images'])
            
            logger.info(f"Metadata uploaded for image {image_uuid} in session {session.session_uuid}")
            
            return Response(
                {
                    'metadata': OfflineImageMetadataSerializer(metadata).data,
                    'upload_item': ImageUploadItemSerializer(upload_item).data,
                },
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error uploading metadata: {e}", exc_info=True)
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], url_path='upload-binary')
    @transaction.atomic
    def upload_binary(self, request, pk=None):
        """
        Upload binary data for an image (idempotent).
        
        This is the SECOND step in the upload process.
        Binary is uploaded after metadata is confirmed.
        """
        session = self.get_object()
        
        serializer = BinaryUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        image_uuid = serializer.validated_data['image_uuid']
        file_content = serializer.validated_data['file']
        
        try:
            # Get metadata
            metadata = get_object_or_404(
                OfflineImageMetadata,
                image_uuid=image_uuid
            )
            
            # Validate metadata is uploaded first
            if metadata.status == 'PENDING':
                return Response(
                    {'detail': 'Metadata must be uploaded before binary'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Calculate checksum of uploaded file
            file_content.seek(0)
            file_bytes = file_content.read()
            calculated_checksum = hashlib.sha256(file_bytes).hexdigest()
            
            # Validate checksum
            if calculated_checksum != metadata.checksum:
                return Response(
                    {
                        'detail': 'Checksum mismatch',
                        'expected': metadata.checksum,
                        'received': calculated_checksum
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Upload binary
            file_content.seek(0)
            uploaded_image = OfflineImageSyncService.upload_binary(
                image_uuid=image_uuid,
                file_content=file_bytes,
                user=request.user,
            )
            
            # Update upload item status
            upload_item = ImageUploadItem.objects.filter(
                session=session,
                metadata=metadata
            ).first()
            
            if upload_item:
                upload_item.update_status('BINARY_UPLOADED')
            
            logger.info(f"Binary uploaded for image {image_uuid} in session {session.session_uuid}")
            
            return Response(
                {
                    'detail': 'Binary uploaded successfully',
                    'image': {
                        'id': uploaded_image.id,
                        'file_key': uploaded_image.file_key,
                    }
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error uploading binary: {e}", exc_info=True)
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], url_path='acknowledge')
    @transaction.atomic
    def acknowledge(self, request, pk=None):
        """
        Acknowledge successful upload (idempotent).
        
        This is the FINAL step. Client should call this after receiving
        confirmation that the image was successfully stored.
        """
        session = self.get_object()
        
        image_uuid = request.data.get('image_uuid')
        if not image_uuid:
            return Response(
                {'detail': 'image_uuid is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            metadata = get_object_or_404(
                OfflineImageMetadata,
                image_uuid=image_uuid
            )
            
            # Acknowledge upload
            OfflineImageSyncService.acknowledge_upload(
                image_uuid=image_uuid,
                user=request.user,
            )
            
            # Update upload item status
            upload_item = ImageUploadItem.objects.filter(
                session=session,
                metadata=metadata
            ).first()
            
            if upload_item:
                upload_item.update_status('ACK_RECEIVED')
            
            logger.info(f"ACK received for image {image_uuid} in session {session.session_uuid}")
            
            return Response(
                {'detail': 'Upload acknowledged'},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error acknowledging upload: {e}", exc_info=True)
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'], url_path='status')
    def get_status(self, request, pk=None):
        """Get current status of the upload session."""
        session = self.get_object()
        return Response(
            ImageUploadSessionSerializer(session).data,
            status=status.HTTP_200_OK
        )


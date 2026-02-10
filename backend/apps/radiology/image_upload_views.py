"""
API views for Image Upload Session (Offline-First Imaging Upload).
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError

from .image_upload_session_models import ImageUploadSession
from .image_upload_serializers import (
    ImageUploadSessionSerializer,
    ImageUploadSessionCreateSerializer,
    ImageUploadMetadataSerializer,
    ImageUploadBinarySerializer,
    ImageUploadBinaryResponseSerializer,
    ImageUploadAcknowledgeSerializer,
    ImageUploadAcknowledgeResponseSerializer,
)
from .image_upload_service import ImageUploadService
from .models import RadiologyRequest as RadiologyOrder

logger = logging.getLogger(__name__)


class ImageUploadSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Image Upload Sessions.
    
    Supports:
    - Creating upload sessions
    - Uploading metadata
    - Uploading binary data (resumable)
    - Acknowledging uploads
    - Listing pending/failed uploads
    """
    serializer_class = ImageUploadSessionSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'session_id'
    lookup_value_regex = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    
    def get_queryset(self):
        """Get upload sessions, optionally filtered by radiology order."""
        queryset = ImageUploadSession.objects.select_related(
            'radiology_order', 'created_by'
        ).all()
        
        radiology_order_id = self.request.query_params.get('radiology_order_id')
        if radiology_order_id:
            queryset = queryset.filter(radiology_order_id=radiology_order_id)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def create_session(self, request):
        """
        Create a new upload session.
        
        This is the first step in the offline-first upload process.
        """
        serializer = ImageUploadSessionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Verify radiology order exists
            radiology_order = get_object_or_404(
                RadiologyRequest,
                pk=serializer.validated_data['radiology_order_id']
            )
            
            # Create upload session
            session = ImageUploadService.create_upload_session(
                radiology_order_id=radiology_order.id,
                local_file_path=serializer.validated_data['local_file_path'],
                file_name=serializer.validated_data['file_name'],
                content_type=serializer.validated_data['content_type'],
                created_by_id=request.user.id,
                metadata=serializer.validated_data.get('metadata', {})
            )
            
            return Response(
                ImageUploadSessionSerializer(session).data,
                status=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error creating upload session: {e}")
            return Response(
                {'error': 'Failed to create upload session'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def upload_metadata(self, request, session_id=None):
        """
        Upload metadata to server (step 2).
        
        This must be done before uploading binary data.
        """
        try:
            result = ImageUploadService.upload_metadata(session_id)
            serializer = ImageUploadMetadataSerializer(result)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error uploading metadata for session {session_id}: {e}")
            return Response(
                {'error': 'Failed to upload metadata'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def upload_binary(self, request, session_id=None):
        """
        Upload binary data to server (step 3, resumable).
        
        Supports resumable uploads via resume_from parameter.
        """
        serializer = ImageUploadBinarySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            result = ImageUploadService.upload_binary(
                session_id=session_id,
                resume_from=serializer.validated_data.get('resume_from', 0),
                chunk_size=serializer.validated_data.get('chunk_size', 1048576)
            )
            response_serializer = ImageUploadBinaryResponseSerializer(result)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error uploading binary for session {session_id}: {e}")
            return Response(
                {'error': 'Failed to upload binary data'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, session_id=None):
        """
        Acknowledge successful upload (step 4).
        
        After acknowledgment, local file can be safely deleted.
        """
        serializer = ImageUploadAcknowledgeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            result = ImageUploadService.acknowledge_upload(
                session_id=session_id,
                server_image_id=serializer.validated_data['server_image_id']
            )
            response_serializer = ImageUploadAcknowledgeResponseSerializer(result)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error acknowledging upload for session {session_id}: {e}")
            return Response(
                {'error': 'Failed to acknowledge upload'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get all pending upload sessions."""
        radiology_order_id = request.query_params.get('radiology_order_id')
        sessions = ImageUploadService.get_pending_uploads(
            radiology_order_id=int(radiology_order_id) if radiology_order_id else None
        )
        serializer = ImageUploadSessionSerializer(sessions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def failed(self, request):
        """Get all failed upload sessions that can be retried."""
        radiology_order_id = request.query_params.get('radiology_order_id')
        sessions = ImageUploadService.get_failed_uploads(
            radiology_order_id=int(radiology_order_id) if radiology_order_id else None
        )
        serializer = ImageUploadSessionSerializer(sessions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def retry(self, request, session_id=None):
        """Retry a failed upload session."""
        try:
            session = get_object_or_404(ImageUploadSession, session_id=session_id)
            if not session.can_retry():
                return Response(
                    {'error': 'Session cannot be retried'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            session.mark_as_queued()
            serializer = ImageUploadSessionSerializer(session)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error retrying upload session {session_id}: {e}")
            return Response(
                {'error': 'Failed to retry upload'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


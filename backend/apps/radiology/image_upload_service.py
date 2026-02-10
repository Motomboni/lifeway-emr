"""
Image Upload Service for Offline-First Imaging Upload System.

This service handles:
- Creating upload sessions
- Uploading metadata first
- Uploading binary data with resumable support
- Checksum verification
- Retry logic
- Server acknowledgment
"""
import logging
import os
import uuid
from django.core.files.uploadedfile import UploadedFile
from django.core.files.base import ContentFile
from django.db import transaction, models
from django.utils import timezone
from django.core.exceptions import ValidationError

from .image_upload_session_models import ImageUploadSession
from .models import RadiologyRequest
from .pacs_lite_service import PACSLiteService
from .pacs_lite_models import RadiologyImage

logger = logging.getLogger(__name__)


class ImageUploadService:
    """Service for handling offline-first image uploads."""
    
    @staticmethod
    @transaction.atomic
    def create_upload_session(
        radiology_order_id: int,
        local_file_path: str,
        file_name: str,
        content_type: str,
        created_by_id: int,
        metadata: dict = None
    ) -> ImageUploadSession:
        """
        Create a new upload session for an image.
        
        Args:
            radiology_order_id: ID of the radiology order
            local_file_path: Path to local file
            file_name: Original filename
            content_type: MIME type
            created_by_id: User ID who initiated upload
            metadata: Additional metadata
        
        Returns:
            ImageUploadSession instance
        """
        # Verify file exists
        if not os.path.exists(local_file_path):
            raise ValidationError(f"Local file not found: {local_file_path}")
        
        # Get file size
        file_size = os.path.getsize(local_file_path)
        if file_size == 0:
            raise ValidationError("File is empty")
        
        # Calculate checksum
        checksum = ImageUploadSession.calculate_checksum(local_file_path)
        
        # Check for duplicate (same checksum for same order)
        existing = ImageUploadSession.objects.filter(
            radiology_order_id=radiology_order_id,
            checksum=checksum,
            status__in=['QUEUED', 'METADATA_UPLOADING', 'METADATA_UPLOADED', 'BINARY_UPLOADING', 'SYNCED', 'ACK_RECEIVED']
        ).first()
        
        if existing:
            logger.info(f"Duplicate upload detected for checksum {checksum}, returning existing session")
            return existing
        
        # Create session
        session = ImageUploadSession.objects.create(
            radiology_order_id=radiology_order_id,
            local_file_path=local_file_path,
            file_name=file_name,
            file_size=file_size,
            content_type=content_type,
            checksum=checksum,
            created_by_id=created_by_id,
            metadata=metadata or {},
            status='QUEUED'
        )
        
        logger.info(f"Created upload session {session.session_id} for file {file_name}")
        return session
    
    @staticmethod
    @transaction.atomic
    def upload_metadata(session_id: str) -> dict:
        """
        Upload metadata to server (first step).
        
        Args:
            session_id: UUID of the upload session
        
        Returns:
            Dict with upload information
        """
        try:
            session = ImageUploadSession.objects.select_for_update().get(session_id=session_id)
        except ImageUploadSession.DoesNotExist:
            raise ValidationError(f"Upload session not found: {session_id}")
        
        # Check if already uploaded
        if session.metadata_uploaded:
            logger.info(f"Metadata already uploaded for session {session_id}")
            return {
                'session_id': str(session.session_id),
                'status': session.status,
                'metadata_uploaded': True
            }
        
        # Mark as uploading
        session.mark_metadata_uploading()
        
        try:
            # Verify file still exists
            if not os.path.exists(session.local_file_path):
                raise ValidationError(f"Local file no longer exists: {session.local_file_path}")
            
            # Verify checksum
            if not session.verify_checksum(session.local_file_path):
                raise ValidationError("File checksum verification failed")
            
            # Mark as uploaded (actual server upload would happen here)
            # For now, we just mark it as uploaded
            session.mark_metadata_uploaded()
            
            logger.info(f"Metadata uploaded for session {session_id}")
            
            return {
                'session_id': str(session.session_id),
                'status': session.status,
                'metadata_uploaded': True,
                'next_step': 'upload_binary'
            }
        except Exception as e:
            logger.error(f"Error uploading metadata for session {session_id}: {e}")
            session.mark_failed(str(e), 'METADATA_UPLOAD_ERROR')
            raise
    
    @staticmethod
    @transaction.atomic
    def upload_binary(
        session_id: str,
        resume_from: int = 0,
        chunk_size: int = 1024 * 1024  # 1MB chunks
    ) -> dict:
        """
        Upload binary data to server (second step, resumable).
        
        Args:
            session_id: UUID of the upload session
            resume_from: Byte position to resume from
            chunk_size: Size of each upload chunk
        
        Returns:
            Dict with upload progress
        """
        try:
            session = ImageUploadSession.objects.select_for_update().get(session_id=session_id)
        except ImageUploadSession.DoesNotExist:
            raise ValidationError(f"Upload session not found: {session_id}")
        
        # Verify metadata is uploaded first
        if not session.metadata_uploaded:
            raise ValidationError("Metadata must be uploaded before binary data")
        
        # Check if already uploaded
        if session.binary_uploaded:
            logger.info(f"Binary already uploaded for session {session_id}")
            return {
                'session_id': str(session.session_id),
                'status': session.status,
                'binary_uploaded': True,
                'progress_percent': 100
            }
        
        # Verify file still exists
        if not os.path.exists(session.local_file_path):
            raise ValidationError(f"Local file no longer exists: {session.local_file_path}")
        
        # Verify checksum
        if not session.verify_checksum(session.local_file_path):
            raise ValidationError("File checksum verification failed")
        
        try:
            # Mark as uploading
            session.mark_binary_uploading(resume_from)
            
            # Read file in chunks and upload
            with open(session.local_file_path, 'rb') as f:
                f.seek(resume_from)
                
                # In a real implementation, this would upload to S3/MinIO/etc.
                # For now, we simulate the upload
                bytes_uploaded = resume_from
                
                while bytes_uploaded < session.file_size:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    # Simulate upload (in real implementation, upload chunk to server)
                    # For now, we'll just mark progress
                    bytes_uploaded += len(chunk)
                    
                    # Update progress
                    session.bytes_uploaded = bytes_uploaded
                    session.upload_progress_percent = (bytes_uploaded / session.file_size) * 100
                    session.save()
            
                # Store image using PACS-lite service
            radiology_order = session.radiology_order
            
            # Get or create study and series
            study = PACSLiteService.create_study_for_order(radiology_order)
            series = PACSLiteService.create_series_for_study(
                study=study,
                modality=session.metadata.get('modality', 'CT'),
                series_description=session.file_name
            )
            
            # Read file content
            with open(session.local_file_path, 'rb') as f:
                file_content = f.read()
            
            # Generate file key
            file_key = PACSLiteService.generate_file_key(
                study_uid=study.study_uid,
                series_uid=series.series_uid,
                image_uid=str(uuid.uuid4()),
                filename=session.file_name
            )
            
            # Store image binary
            stored_path = PACSLiteService.store_image(
                file_content=file_content,
                file_key=file_key,
                content_type=session.content_type
            )
            
            # Create RadiologyImage record
            from .pacs_lite_models import RadiologyImage
            image = RadiologyImage.objects.create(
                series=series,
                image_uid=str(uuid.uuid4()),
                file_key=stored_path,
                filename=session.file_name,
                file_size=session.file_size,
                mime_type=session.content_type,
                checksum=session.checksum,
                image_metadata=session.metadata
            )
            
            # Mark as synced
            session.mark_synced()
            
            logger.info(f"Binary uploaded for session {session_id}, image ID: {image.id}")
            
            return {
                'session_id': str(session.session_id),
                'status': session.status,
                'binary_uploaded': True,
                'progress_percent': 100,
                'image_id': image.id
            }
        except Exception as e:
            logger.error(f"Error uploading binary for session {session_id}: {e}")
            session.mark_failed(str(e), 'BINARY_UPLOAD_ERROR')
            raise
    
    @staticmethod
    @transaction.atomic
    def acknowledge_upload(session_id: str, server_image_id: int) -> dict:
        """
        Acknowledge successful upload (final step).
        
        After acknowledgment, local file can be safely deleted.
        
        Args:
            session_id: UUID of the upload session
            server_image_id: ID of the image record on server
        
        Returns:
            Dict with acknowledgment info
        """
        try:
            session = ImageUploadSession.objects.select_for_update().get(session_id=session_id)
        except ImageUploadSession.DoesNotExist:
            raise ValidationError(f"Upload session not found: {session_id}")
        
        # Verify binary is uploaded
        if not session.binary_uploaded:
            raise ValidationError("Binary must be uploaded before acknowledgment")
        
        # Mark as acknowledged
        session.mark_ack_received(server_image_id)
        
        logger.info(f"Upload acknowledged for session {session_id}, image ID: {server_image_id}")
        
        return {
            'session_id': str(session.session_id),
            'status': session.status,
            'ack_received': True,
            'safe_to_delete_local': True
        }
    
    @staticmethod
    def get_pending_uploads(radiology_order_id: int = None) -> list:
        """
        Get all pending upload sessions.
        
        Args:
            radiology_order_id: Optional filter by radiology order
        
        Returns:
            List of pending upload sessions
        """
        queryset = ImageUploadSession.objects.filter(
            status__in=['QUEUED', 'METADATA_UPLOADING', 'BINARY_UPLOADING']
        )
        
        if radiology_order_id:
            queryset = queryset.filter(radiology_order_id=radiology_order_id)
        
        return list(queryset)
    
    @staticmethod
    def get_failed_uploads(radiology_order_id: int = None) -> list:
        """
        Get all failed upload sessions that can be retried.
        
        Args:
            radiology_order_id: Optional filter by radiology order
        
        Returns:
            List of failed upload sessions
        """
        queryset = ImageUploadSession.objects.filter(
            status='FAILED'
        ).filter(
            retry_count__lt=models.F('max_retries')
        )
        
        if radiology_order_id:
            queryset = queryset.filter(radiology_order_id=radiology_order_id)
        
        return list(queryset)
    
    @staticmethod
    def cleanup_completed_sessions(days_old: int = 7):
        """
        Clean up completed sessions older than specified days.
        
        This should only be called after local files have been deleted.
        
        Args:
            days_old: Number of days old sessions should be before cleanup
        """
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=days_old)
        
        deleted_count = ImageUploadSession.objects.filter(
            status='ACK_RECEIVED',
            server_ack_at__lt=cutoff_date
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} completed upload sessions")
        return deleted_count


"""
Offline Image Sync Service - PACS-lite Implementation

Per EMR Context Document v2 (LOCKED):
- Metadata syncs before binaries
- No image is deleted locally until server ACK
- Images are immutable
- No overwrite allowed
- Checksums validated server-side

This service handles the background sync of offline images.
"""
import hashlib
import logging
from typing import Optional, Dict, Any
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction

from .offline_image_models import OfflineImageMetadata
from .pacs_lite_models import RadiologyStudy, RadiologySeries, RadiologyImage
from .pacs_lite_service import PACSLiteService
from .models import RadiologyOrder
from apps.users.models import User

logger = logging.getLogger(__name__)


class OfflineImageSyncService:
    """
    Service for syncing offline radiology images.
    
    Flow:
    1. Queue metadata (client-side)
    2. Upload metadata (this service)
    3. Validate metadata
    4. Upload binary (this service)
    5. Validate checksum
    6. Create RadiologyImage
    7. Send ACK to client
    """
    
    @staticmethod
    @transaction.atomic
    def upload_metadata(
        image_uuid: str,
        radiology_order_id: int,
        filename: str,
        file_size: int,
        mime_type: str,
        checksum: str,
        image_metadata: Dict[str, Any],
        user: User,
    ) -> OfflineImageMetadata:
        """
        Upload metadata for an offline image (FIRST STEP).
        
        Per EMR Context Document v2: "Metadata syncs before binaries"
        
        Args:
            image_uuid: UUID of the image (from client)
            radiology_order_id: ID of the radiology order
            filename: Original filename
            file_size: File size in bytes
            mime_type: MIME type
            checksum: SHA-256 checksum
            image_metadata: Image metadata (DICOM tags, EXIF, etc.)
            user: User uploading the image
        
        Returns:
            OfflineImageMetadata instance
        
        Raises:
            ValidationError: If validation fails
        """
        # Validate radiology order exists
        try:
            radiology_order = RadiologyOrder.objects.get(pk=radiology_order_id)
        except RadiologyOrder.DoesNotExist:
            raise ValidationError(
                f"Radiology order {radiology_order_id} does not exist."
            )
        
        # Validate checksum format
        if len(checksum) != 64:
            raise ValidationError(
                f"Checksum must be SHA-256 (64 hex characters). Got {len(checksum)} characters."
            )
        
        # Check if image with this UUID already exists
        existing = OfflineImageMetadata.objects.filter(image_uuid=image_uuid).first()
        if existing:
            if existing.status == 'ACK_RECEIVED':
                # Already synced, return existing
                logger.info(f"Image {image_uuid} already synced (ACK_RECEIVED)")
                return existing
            elif existing.status in ['PENDING', 'METADATA_UPLOADED', 'BINARY_UPLOADED']:
                # Update existing metadata (retry)
                existing.filename = filename
                existing.file_size = file_size
                existing.mime_type = mime_type
                existing.checksum = checksum
                existing.image_metadata = image_metadata
                existing.retry_count += 1
                existing.last_retry_at = timezone.now()
                existing.full_clean()
                existing.save()
                logger.info(f"Updated metadata for image {image_uuid} (retry {existing.retry_count})")
                return existing
        
        # Create new metadata record
        metadata = OfflineImageMetadata.objects.create(
            image_uuid=image_uuid,
            radiology_order=radiology_order,
            filename=filename,
            file_size=file_size,
            mime_type=mime_type,
            checksum=checksum,
            image_metadata=image_metadata,
            status='METADATA_UPLOADED',  # Metadata uploaded successfully
            metadata_uploaded_at=timezone.now(),
        )
        
        logger.info(f"Metadata uploaded for image {image_uuid} (order {radiology_order_id})")
        return metadata
    
    @staticmethod
    @transaction.atomic
    def upload_binary(
        image_uuid: str,
        file_content: bytes,
        user: User,
    ) -> RadiologyImage:
        """
        Upload binary for an offline image (SECOND STEP).
        
        Per EMR Context Document v2: "Binaries uploaded after metadata"
        
        Args:
            image_uuid: UUID of the image
            file_content: Binary content of the file
            user: User uploading the image
        
        Returns:
            RadiologyImage instance
        
        Raises:
            ValidationError: If validation fails
        """
        # Get metadata (must exist and be in METADATA_UPLOADED status)
        try:
            metadata = OfflineImageMetadata.objects.get(
                image_uuid=image_uuid,
                status='METADATA_UPLOADED'
            )
        except OfflineImageMetadata.DoesNotExist:
            raise ValidationError(
                f"Metadata for image {image_uuid} not found or not ready for binary upload. "
                "Metadata must be uploaded first."
            )
        
        # Calculate checksum from file content
        calculated_checksum = hashlib.sha256(file_content).hexdigest()
        
        # ❌ GOVERNANCE RULE: Validate checksum server-side
        if calculated_checksum.lower() != metadata.checksum.lower():
            metadata.mark_failed(
                reason=f"Checksum mismatch. Expected: {metadata.checksum}, Got: {calculated_checksum}"
            )
            raise ValidationError(
                f"Checksum validation failed. Expected: {metadata.checksum}, Got: {calculated_checksum}. "
                "Per EMR Context Document v2, checksums are validated server-side."
            )
        
        # Check if image with this checksum already exists (immutability)
        existing_image = RadiologyImage.objects.filter(checksum=calculated_checksum).first()
        if existing_image:
            # Image already exists, mark metadata as ACK_RECEIVED
            metadata.status = 'ACK_RECEIVED'
            metadata.ack_received_at = timezone.now()
            metadata.save()
            logger.info(f"Image {image_uuid} already exists (checksum match), returning existing")
            return existing_image
        
        # Validate file size matches metadata
        if len(file_content) != metadata.file_size:
            metadata.mark_failed(
                reason=f"File size mismatch. Expected: {metadata.file_size}, Got: {len(file_content)}"
            )
            raise ValidationError(
                f"File size mismatch. Expected: {metadata.file_size}, Got: {len(file_content)}"
            )
        
        # Get or create study for radiology order
        study = PACSLiteService.create_study_for_order(
            radiology_order=metadata.radiology_order,
            study_description=metadata.image_metadata.get('study_description', ''),
            modality=metadata.image_metadata.get('modality', ''),
        )
        
        # Get or create series for study (default series if not specified)
        series_uid = metadata.image_metadata.get('series_uid')
        series = PACSLiteService.create_series_for_study(
            study=study,
            series_uid=series_uid,
            series_description=metadata.image_metadata.get('series_description', ''),
            modality=metadata.image_metadata.get('modality', ''),
        )
        
        # Generate file key for storage
        image_uid = metadata.image_metadata.get('image_uid') or str(uuid.uuid4())
        file_key = PACSLiteService.generate_file_key(
            study_uid=study.study_uid,
            series_uid=series.series_uid,
            image_uid=image_uid,
            filename=metadata.filename,
        )
        
        # Store image in PACS-lite storage
        stored_file_key = PACSLiteService.store_image(
            file_content=file_content,
            file_key=file_key,
            content_type=metadata.mime_type,
        )
        
        # Create RadiologyImage record (immutable)
        image = RadiologyImage.objects.create(
            series=series,
            offline_metadata=metadata,
            image_uid=image_uid,
            file_key=stored_file_key,
            filename=metadata.filename,
            file_size=metadata.file_size,
            mime_type=metadata.mime_type,
            image_metadata=metadata.image_metadata,
            instance_number=metadata.image_metadata.get('instance_number'),
            checksum=calculated_checksum,
            uploaded_by=user,
            validated_at=timezone.now(),
        )
        
        # Mark metadata as binary uploaded
        metadata.mark_binary_uploaded()
        
        logger.info(f"Binary uploaded for image {image_uuid}, stored at {stored_file_key}, ready for ACK")
        
        return image
    
    @staticmethod
    @transaction.atomic
    def acknowledge_upload(
        image_uuid: str,
    ) -> OfflineImageMetadata:
        """
        Acknowledge successful upload (THIRD STEP - Safe to delete local copy).
        
        Per EMR Context Document v2: "Local copy deleted ONLY after ACK"
        
        Args:
            image_uuid: UUID of the image
        
        Returns:
            OfflineImageMetadata instance with ACK_RECEIVED status
        
        Raises:
            ValidationError: If validation fails
        """
        # Get metadata (must be in BINARY_UPLOADED status)
        try:
            metadata = OfflineImageMetadata.objects.get(
                image_uuid=image_uuid,
                status='BINARY_UPLOADED'
            )
        except OfflineImageMetadata.DoesNotExist:
            raise ValidationError(
                f"Metadata for image {image_uuid} not found or not ready for ACK. "
                "Binary must be uploaded first."
            )
        
        # Verify RadiologyImage exists
        if not hasattr(metadata, 'server_image'):
            raise ValidationError(
                f"RadiologyImage not found for image {image_uuid}. "
                "Cannot acknowledge upload without server image record."
            )
        
        # Mark as ACK_RECEIVED (safe to delete local copy)
        metadata.mark_ack_received()
        
        logger.info(f"ACK received for image {image_uuid} - safe to delete local copy")
        
        return metadata
    
    @staticmethod
    def get_pending_uploads(radiology_order_id: Optional[int] = None) -> list:
        """
        Get list of pending uploads (for client-side sync).
        
        Args:
            radiology_order_id: Optional filter by radiology order
        
        Returns:
            List of OfflineImageMetadata instances with pending status
        """
        queryset = OfflineImageMetadata.objects.filter(
            status__in=['PENDING', 'METADATA_UPLOADED', 'BINARY_UPLOADED']
        )
        
        if radiology_order_id:
            queryset = queryset.filter(radiology_order_id=radiology_order_id)
        
        return list(queryset.order_by('created_at'))
    
    @staticmethod
    def get_failed_uploads(radiology_order_id: Optional[int] = None) -> list:
        """
        Get list of failed uploads (for manual intervention).
        
        Args:
            radiology_order_id: Optional filter by radiology order
        
        Returns:
            List of OfflineImageMetadata instances with FAILED status
        """
        queryset = OfflineImageMetadata.objects.filter(status='FAILED')
        
        if radiology_order_id:
            queryset = queryset.filter(radiology_order_id=radiology_order_id)
        
        return list(queryset.order_by('-failed_at'))


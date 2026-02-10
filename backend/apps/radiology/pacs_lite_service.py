"""
PACS-lite Service - Storage Management and Viewer URL Generation

Per EMR Context Document v2 (LOCKED):
- PACS-lite DOES: Store DICOM/JPEG, Group by Study/Series, Expose viewer URLs, Enforce read-only access
- PACS-lite DOES NOT: Manage modality devices, Do HL7 routing, Own patient records

Storage Rule (Critical):
- EMR DB stores: study_uid, series_uid, file_keys
- Images live in: S3 / MinIO / filesystem

Viewer Strategy:
- OHIF Viewer (recommended) or lightweight DICOM viewer
- Access controlled via signed URLs
"""
import logging
import uuid
from typing import Optional, Dict, Any, List
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from .pacs_lite_models import RadiologyStudy, RadiologySeries, RadiologyImage
from .models import RadiologyOrder
from apps.users.models import User

logger = logging.getLogger(__name__)


class PACSLiteService:
    """
    PACS-lite service for managing radiology image storage and viewer access.
    
    Responsibilities:
    1. Create Study/Series structure
    2. Store images in S3/MinIO/filesystem
    3. Generate signed viewer URLs
    4. Enforce read-only access
    """
    
    @staticmethod
    @transaction.atomic
    def create_study_for_order(
        radiology_order: RadiologyOrder,
        study_uid: Optional[str] = None,
        study_date: Optional[str] = None,
        study_description: Optional[str] = None,
        modality: Optional[str] = None,
    ) -> RadiologyStudy:
        """
        Create a study for a radiology order.
        
        Per PACS-lite: One study per RadiologyOrder.
        
        Args:
            radiology_order: RadiologyOrder instance
            study_uid: DICOM StudyInstanceUID (optional, generated if not provided)
            study_date: Study date (optional)
            study_description: Study description (optional)
            modality: Modality (optional)
        
        Returns:
            RadiologyStudy instance
        """
        # Check if study already exists
        if hasattr(radiology_order, 'study'):
            logger.info(f"Study already exists for order {radiology_order.id}")
            return radiology_order.study
        
        # Get patient information from visit
        visit = radiology_order.visit
        patient = visit.patient
        
        # Create study
        study = RadiologyStudy.objects.create(
            study_uid=study_uid or str(uuid.uuid4()),
            radiology_order=radiology_order,
            study_date=study_date or timezone.now().date(),
            study_description=study_description or radiology_order.clinical_indication,
            modality=modality or getattr(radiology_order, 'imaging_type', ''),
            patient_name=patient.get_full_name(),
            patient_id=str(patient.id),
        )
        
        logger.info(f"Created study {study.study_uid} for order {radiology_order.id}")
        return study
    
    @staticmethod
    @transaction.atomic
    def create_series_for_study(
        study: RadiologyStudy,
        series_uid: Optional[str] = None,
        series_number: Optional[int] = None,
        series_description: Optional[str] = None,
        modality: Optional[str] = None,
    ) -> RadiologySeries:
        """
        Create a series within a study.
        
        Per PACS-lite: Multiple series per study.
        
        Args:
            study: RadiologyStudy instance
            series_uid: DICOM SeriesInstanceUID (optional, generated if not provided)
            series_number: Series number (optional)
            series_description: Series description (optional)
            modality: Modality (optional)
        
        Returns:
            RadiologySeries instance
        """
        # Check if series with this UID already exists for this study
        if series_uid:
            existing_series = RadiologySeries.objects.filter(
                study=study,
                series_uid=series_uid
            ).first()
            if existing_series:
                logger.info(f"Series {series_uid} already exists for study {study.study_uid}, returning existing")
                return existing_series
        
        # Create new series
        series = RadiologySeries.objects.create(
            series_uid=series_uid or str(uuid.uuid4()),
            study=study,
            series_number=series_number,
            series_description=series_description,
            modality=modality or study.modality,
        )
        
        logger.info(f"Created series {series.series_uid} for study {study.study_uid}")
        return series
    
    @staticmethod
    def generate_file_key(
        study_uid: str,
        series_uid: str,
        image_uid: str,
        filename: str,
    ) -> str:
        """
        Generate file key for storage (S3/MinIO/filesystem).
        
        Structure: radiology/{study_uid}/{series_uid}/{image_uid}/{filename}
        
        Args:
            study_uid: Study UID
            series_uid: Series UID
            image_uid: Image UID
            filename: Original filename
        
        Returns:
            File key/path
        """
        # Sanitize filename
        safe_filename = filename.replace(' ', '_').replace('/', '_')
        
        # Generate file key
        file_key = f"radiology/{study_uid}/{series_uid}/{image_uid}/{safe_filename}"
        
        return file_key
    
    @staticmethod
    def get_storage_backend():
        """
        Get storage backend (S3, MinIO, or filesystem).
        
        Returns:
            Storage backend instance
        """
        from django.core.files.storage import default_storage
        
        # Check if custom storage is configured
        if hasattr(settings, 'RADIOLOGY_STORAGE') and settings.RADIOLOGY_STORAGE:
            # Import the storage class directly
            try:
                module_path, class_name = settings.RADIOLOGY_STORAGE.rsplit('.', 1)
                module = __import__(module_path, fromlist=[class_name])
                storage_class = getattr(module, class_name)
                return storage_class()
            except (ImportError, AttributeError, ValueError) as e:
                logger.warning(f"Could not import custom storage {settings.RADIOLOGY_STORAGE}: {e}. Using default storage.")
                return default_storage
        
        # Use default storage (filesystem or configured storage)
        return default_storage
    
    @staticmethod
    def store_image(
        file_content: bytes,
        file_key: str,
        content_type: str,
    ) -> str:
        """
        Store image in storage (S3/MinIO/filesystem).
        
        Args:
            file_content: Binary file content
            file_key: File key/path
            content_type: Content type (MIME type)
        
        Returns:
            Stored file key
        """
        from django.core.files.base import ContentFile
        
        storage = PACSLiteService.get_storage_backend()
        
        # Create ContentFile from bytes
        filename = file_key.split('/')[-1]
        file_obj = ContentFile(file_content, name=filename)
        
        # Save file
        saved_path = storage.save(file_key, file_obj)
        
        logger.info(f"Stored image at {saved_path}")
        return saved_path
    
    @staticmethod
    def generate_viewer_url(
        study_uid: str,
        user: User,
        expires_in: int = 3600,  # 1 hour default
    ) -> str:
        """
        Generate signed viewer URL for OHIF Viewer or lightweight DICOM viewer.
        
        Per PACS-lite: Access controlled via signed URLs.
        
        Args:
            study_uid: Study UID
            user: User requesting access (for access control)
            expires_in: URL expiration time in seconds (default: 1 hour)
        
        Returns:
            Signed viewer URL
        """
        # Check if OHIF viewer is configured
        ohif_viewer_url = getattr(settings, 'OHIF_VIEWER_URL', None)
        
        if ohif_viewer_url:
            # Generate OHIF viewer URL with study UID
            viewer_url = f"{ohif_viewer_url}?studyInstanceUIDs={study_uid}"
        else:
            # Fallback to lightweight viewer or custom viewer
            viewer_url = f"/radiology/viewer/{study_uid}/"
        
        # Generate signed token (if using signed URLs)
        if hasattr(settings, 'RADIOLOGY_SIGNED_URLS') and settings.RADIOLOGY_SIGNED_URLS:
            from django.core.signing import Signer
            signer = Signer()
            signed_token = signer.sign(f"{study_uid}:{user.id}:{expires_in}")
            viewer_url = f"{viewer_url}&token={signed_token}&expires={expires_in}"
        
        logger.info(f"Generated viewer URL for study {study_uid} (user {user.id})")
        return viewer_url
    
    @staticmethod
    def generate_image_url(
        image: RadiologyImage,
        user: User,
        expires_in: int = 3600,  # 1 hour default
    ) -> str:
        """
        Generate signed URL for individual image access.
        
        Per PACS-lite: Read-only access enforced.
        
        Args:
            image: RadiologyImage instance
            user: User requesting access
            expires_in: URL expiration time in seconds (default: 1 hour)
        
        Returns:
            Signed image URL
        """
        storage = PACSLiteService.get_storage_backend()
        
        # Check if storage supports URL generation
        if hasattr(storage, 'url'):
            # Generate URL (may be signed if using S3/MinIO)
            url = storage.url(image.file_key)
        else:
            # Fallback to direct file access (with signed token)
            from django.core.signing import Signer
            signer = Signer()
            signed_token = signer.sign(f"{image.image_uid}:{user.id}:{expires_in}")
            url = f"/radiology/images/{image.image_uid}/?token={signed_token}&expires={expires_in}"
        
        logger.info(f"Generated image URL for {image.image_uid} (user {user.id})")
        return url
    
    @staticmethod
    def get_study_images(study_uid: str) -> List[RadiologyImage]:
        """
        Get all images for a study (grouped by series).
        
        Per PACS-lite: Group by Study/Series.
        
        Args:
            study_uid: Study UID
        
        Returns:
            List of RadiologyImage instances
        """
        try:
            study = RadiologyStudy.objects.get(study_uid=study_uid)
            images = RadiologyImage.objects.filter(series__study=study).select_related(
                'series', 'series__study'
            ).order_by('series__series_number', 'instance_number')
            return list(images)
        except RadiologyStudy.DoesNotExist:
            return []
    
    @staticmethod
    def get_series_images(series_uid: str) -> List[RadiologyImage]:
        """
        Get all images for a series.
        
        Args:
            series_uid: Series UID
        
        Returns:
            List of RadiologyImage instances
        """
        try:
            series = RadiologySeries.objects.get(series_uid=series_uid)
            images = RadiologyImage.objects.filter(series=series).order_by('instance_number')
            return list(images)
        except RadiologySeries.DoesNotExist:
            return []


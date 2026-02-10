"""
PACS-lite Models - Study/Series Grouping and Viewer Integration

Per EMR Context Document v2 (LOCKED):
- PACS-lite DOES: Store DICOM/JPEG, Group by Study/Series, Expose viewer URLs, Enforce read-only access
- PACS-lite DOES NOT: Manage modality devices, Do HL7 routing, Own patient records

Storage Rule (Critical):
- EMR DB stores: study_uid, series_uid, file_keys
- Images live in: S3 / MinIO / filesystem
"""
import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class RadiologyStudy(models.Model):
    """
    Radiology Study - Groups images by study.
    
    Per PACS-lite: Groups images by study (one study per RadiologyOrder).
    Study UID is DICOM StudyInstanceUID or generated UUID.
    """
    
    # Study identifier (DICOM StudyInstanceUID or generated UUID)
    study_uid = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="DICOM StudyInstanceUID or generated UUID for study identification"
    )
    
    # Link to radiology order (one study per order)
    radiology_order = models.OneToOneField(
        'radiology.RadiologyOrder',
        on_delete=models.CASCADE,
        related_name='study',
        help_text="Radiology order this study belongs to"
    )
    
    # Study metadata
    study_date = models.DateField(
        null=True,
        blank=True,
        help_text="Study date (from DICOM or imaging date)"
    )
    
    study_description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Study description"
    )
    
    modality = models.CharField(
        max_length=10,
        blank=True,
        help_text="Modality (e.g., CR, CT, MR, US)"
    )
    
    # Patient information (snapshot from visit)
    patient_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Patient name (snapshot from visit)"
    )
    
    patient_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Patient ID (snapshot from visit)"
    )
    
    # Audit fields
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When study was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When study was last updated"
    )
    
    class Meta:
        db_table = 'radiology_studies'
        ordering = ['-study_date', '-created_at']
        indexes = [
            models.Index(fields=['study_uid']),
            models.Index(fields=['radiology_order']),
            models.Index(fields=['study_date']),
        ]
        verbose_name = 'Radiology Study'
        verbose_name_plural = 'Radiology Studies'
    
    def __str__(self):
        return f"Study {self.study_uid} - {self.study_description or 'No description'}"
    
    def save(self, *args, **kwargs):
        """Generate study_uid if not provided."""
        if not self.study_uid:
            self.study_uid = str(uuid.uuid4())
        super().save(*args, **kwargs)


class RadiologySeries(models.Model):
    """
    Radiology Series - Groups images by series within a study.
    
    Per PACS-lite: Groups images by series (multiple series per study).
    Series UID is DICOM SeriesInstanceUID or generated UUID.
    """
    
    # Series identifier (DICOM SeriesInstanceUID or generated UUID)
    series_uid = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="DICOM SeriesInstanceUID or generated UUID for series identification"
    )
    
    # Link to study
    study = models.ForeignKey(
        'radiology.RadiologyStudy',
        on_delete=models.CASCADE,
        related_name='series',
        help_text="Study this series belongs to"
    )
    
    # Series metadata
    series_number = models.IntegerField(
        null=True,
        blank=True,
        help_text="Series number (from DICOM)"
    )
    
    series_description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Series description"
    )
    
    modality = models.CharField(
        max_length=10,
        blank=True,
        help_text="Modality (e.g., CR, CT, MR, US)"
    )
    
    # Audit fields
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When series was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When series was last updated"
    )
    
    class Meta:
        db_table = 'radiology_series'
        ordering = ['series_number', 'created_at']
        indexes = [
            models.Index(fields=['series_uid']),
            models.Index(fields=['study']),
            models.Index(fields=['series_number']),
        ]
        verbose_name = 'Radiology Series'
        verbose_name_plural = 'Radiology Series'
        # Ensure unique series per study
        constraints = [
            models.UniqueConstraint(
                fields=['study', 'series_uid'],
                name='unique_series_per_study'
            )
        ]
    
    def __str__(self):
        return f"Series {self.series_uid} - {self.series_description or 'No description'}"
    
    def save(self, *args, **kwargs):
        """Generate series_uid if not provided."""
        if not self.series_uid:
            self.series_uid = str(uuid.uuid4())
        super().save(*args, **kwargs)


class RadiologyImage(models.Model):
    """
    Radiology Image - Individual image file with PACS-lite storage.
    
    Per PACS-lite:
    - Images stored in S3/MinIO/filesystem (not in DB)
    - DB stores: study_uid, series_uid, file_keys
    - Viewer URLs with signed access
    - Read-only access enforced
    """
    
    # Link to series
    series = models.ForeignKey(
        'radiology.RadiologySeries',
        on_delete=models.CASCADE,
        related_name='images',
        null=True,
        blank=True,
        help_text="Series this image belongs to"
    )
    
    # Link to offline metadata (if uploaded via offline sync)
    offline_metadata = models.OneToOneField(
        'radiology.OfflineImageMetadata',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='server_image',
        help_text="Link to offline metadata (if uploaded via offline sync)"
    )
    
    # Image identifier (DICOM SOPInstanceUID or generated UUID)
    image_uid = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        null=True,
        blank=True,
        help_text="DICOM SOPInstanceUID or generated UUID for image identification"
    )
    
    # File storage (PACS-lite: file stored in S3/MinIO/filesystem)
    file_key = models.CharField(
        max_length=500,
        db_index=True,
        null=True,
        blank=True,
        help_text="File key/path in storage (S3 key, MinIO key, or filesystem path)"
    )
    
    # File metadata
    filename = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Original filename"
    )
    
    file_size = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="File size in bytes"
    )
    
    mime_type = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="MIME type (e.g., 'application/dicom', 'image/jpeg')"
    )
    
    # Image metadata (DICOM tags or JPEG EXIF)
    image_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Image metadata (DICOM tags, JPEG EXIF, etc.)"
    )
    
    # Instance number (from DICOM)
    instance_number = models.IntegerField(
        null=True,
        blank=True,
        help_text="Instance number (from DICOM)"
    )
    
    # Validated checksum
    checksum = models.CharField(
        max_length=64,
        db_index=True,
        null=True,
        blank=True,
        help_text="SHA-256 checksum (validated server-side)"
    )
    
    # Audit fields
    uploaded_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='radiology_images_uploaded',
        help_text="User who uploaded this image (Radiology Tech)"
    )
    
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When image was successfully uploaded"
    )
    
    validated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When checksum was validated"
    )
    
    class Meta:
        db_table = 'radiology_images'
        ordering = ['instance_number', 'uploaded_at']
        indexes = [
            models.Index(fields=['series']),
            models.Index(fields=['image_uid']),
            models.Index(fields=['file_key']),
            models.Index(fields=['checksum']),
            models.Index(fields=['uploaded_at']),
        ]
        verbose_name = 'Radiology Image'
        verbose_name_plural = 'Radiology Images'
        # Ensure no duplicate checksums (immutability)
        constraints = [
            models.UniqueConstraint(
                fields=['checksum'],
                name='unique_radiology_image_checksum'
            )
        ]
    
    def __str__(self):
        return f"Image {self.image_uid} - {self.filename}"
    
    @property
    def study(self):
        """Get study through series."""
        return self.series.study
    
    @property
    def radiology_order(self):
        """Get radiology order through study."""
        return self.series.study.radiology_order
    
    def clean(self):
        """Validate radiology image (immutability enforcement)."""
        errors = {}
        
        # ❌ GOVERNANCE RULE: Images are immutable
        if self.pk:
            raise ValidationError(
                "Radiology images are immutable once created. "
                "Cannot modify image ID: %(image_id)s. "
                "If correction is needed, please contact system administrator."
            ) % {'image_id': self.pk}
        
        # Validate required fields for new images (if not from offline sync)
        if not self.pk and not self.offline_metadata:
            if not self.series:
                errors['series'] = "Series is required for new images. Per PACS-lite, images must belong to a series."
            if not self.file_key:
                errors['file_key'] = "File key is required. Per PACS-lite, images must have a file_key for storage."
            if not self.filename:
                errors['filename'] = "Filename is required for new images."
            if not self.file_size:
                errors['file_size'] = "File size is required for new images."
            if not self.mime_type:
                errors['mime_type'] = "MIME type is required for new images."
            if not self.checksum:
                errors['checksum'] = "Checksum is required for new images."
        
        # Validate checksum format
        if self.checksum and len(self.checksum) != 64:
            errors['checksum'] = (
                "Checksum must be SHA-256 (64 hex characters). "
                f"Got {len(self.checksum)} characters."
            )
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Override save to enforce immutability and generate image_uid."""
        # Enforce immutability
        if self.pk:
            raise ValidationError(
                "Radiology images are immutable once created. "
                "Cannot modify existing image."
            )
        
        # Generate image_uid if not provided (required for new images)
        if not self.image_uid:
            if not self.pk:
                # New record - generate UUID
                self.image_uid = str(uuid.uuid4())
        
        # Run validation
        self.full_clean()
        super().save(*args, **kwargs)


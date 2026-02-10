"""
Serializers for Offline Image Sync API.

Per EMR Context Document v2 (LOCKED):
- Metadata syncs before binaries
- No image is deleted locally until server ACK
"""
from rest_framework import serializers
from .offline_image_models import OfflineImageMetadata
from .pacs_lite_models import RadiologyImage
from .models import RadiologyOrder


class OfflineImageMetadataSerializer(serializers.ModelSerializer):
    """Serializer for offline image metadata (read-only after creation)."""
    
    radiology_order_id = serializers.IntegerField(source='radiology_order.id', read_only=True)
    
    class Meta:
        model = OfflineImageMetadata
        fields = [
            'id',
            'image_uuid',
            'radiology_order_id',
            'filename',
            'file_size',
            'mime_type',
            'checksum',
            'image_metadata',
            'status',
            'created_at',
            'metadata_uploaded_at',
            'binary_uploaded_at',
            'ack_received_at',
            'failed_at',
            'failure_reason',
            'retry_count',
            'last_retry_at',
        ]
        read_only_fields = [
            'id',
            'status',
            'created_at',
            'metadata_uploaded_at',
            'binary_uploaded_at',
            'ack_received_at',
            'failed_at',
            'failure_reason',
            'retry_count',
            'last_retry_at',
        ]


class OfflineImageMetadataUploadSerializer(serializers.Serializer):
    """
    Serializer for uploading metadata (FIRST STEP).
    
    Per EMR Context Document v2: "Metadata syncs before binaries"
    """
    image_uuid = serializers.UUIDField(help_text="UUID of the image (generated client-side)")
    radiology_order_id = serializers.IntegerField(help_text="ID of the radiology order")
    filename = serializers.CharField(max_length=255, help_text="Original filename")
    file_size = serializers.IntegerField(min_value=1, help_text="File size in bytes")
    mime_type = serializers.CharField(max_length=100, help_text="MIME type (e.g., 'image/jpeg', 'application/dicom')")
    checksum = serializers.CharField(
        max_length=64,
        min_length=64,
        help_text="SHA-256 checksum (64 hex characters)"
    )
    image_metadata = serializers.JSONField(
        default=dict,
        help_text="Image metadata (DICOM tags, JPEG EXIF, etc.)"
    )
    
    def validate_checksum(self, value):
        """Validate checksum format."""
        if len(value) != 64:
            raise serializers.ValidationError(
                "Checksum must be SHA-256 (64 hex characters)."
            )
        # Validate hex format
        try:
            int(value, 16)
        except ValueError:
            raise serializers.ValidationError(
                "Checksum must be hexadecimal."
            )
        return value.lower()
    
    def validate_radiology_order_id(self, value):
        """Validate radiology order exists."""
        if not RadiologyOrder.objects.filter(pk=value).exists():
            raise serializers.ValidationError(
                f"Radiology order {value} does not exist."
            )
        return value


class OfflineImageBinaryUploadSerializer(serializers.Serializer):
    """
    Serializer for uploading binary (SECOND STEP).
    
    Per EMR Context Document v2: "Binaries uploaded after metadata"
    """
    image_uuid = serializers.UUIDField(help_text="UUID of the image")
    file = serializers.FileField(help_text="Image file (DICOM or JPEG)")
    
    def validate_file(self, value):
        """Validate file."""
        # Check file size (max 100MB)
        if value.size > 100 * 1024 * 1024:
            raise serializers.ValidationError(
                "File size exceeds 100MB limit."
            )
        
        # Check MIME type
        allowed_mime_types = [
            'image/jpeg',
            'image/png',
            'application/dicom',
            'application/dicom+json',
        ]
        if value.content_type not in allowed_mime_types:
            raise serializers.ValidationError(
                f"File type '{value.content_type}' not allowed. "
                f"Allowed types: {', '.join(allowed_mime_types)}"
            )
        
        return value


class RadiologyImageSerializer(serializers.ModelSerializer):
    """Serializer for RadiologyImage (read-only after creation)."""
    
    image_uuid = serializers.UUIDField(source='offline_metadata.image_uuid', read_only=True)
    study_uid = serializers.CharField(source='series.study.study_uid', read_only=True)
    series_uid = serializers.CharField(source='series.series_uid', read_only=True)
    radiology_order_id = serializers.IntegerField(source='series.study.radiology_order.id', read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    
    class Meta:
        model = RadiologyImage
        fields = [
            'id',
            'image_uid',
            'image_uuid',
            'study_uid',
            'series_uid',
            'radiology_order_id',
            'filename',
            'file_key',
            'file_size',
            'mime_type',
            'checksum',
            'image_metadata',
            'instance_number',
            'uploaded_by_name',
            'uploaded_at',
            'validated_at',
        ]
        read_only_fields = [
            'id',
            'image_uid',
            'file_key',
            'checksum',
            'image_metadata',
            'uploaded_by',
            'uploaded_at',
            'validated_at',
        ]


class OfflineImageACKSerializer(serializers.Serializer):
    """
    Serializer for acknowledging upload (THIRD STEP).
    
    Per EMR Context Document v2: "Local copy deleted ONLY after ACK"
    """
    image_uuid = serializers.UUIDField(help_text="UUID of the image to acknowledge")


"""
Serializers for Image Upload Sessions.
"""
from rest_framework import serializers
from .upload_session_models import ImageUploadSession, ImageUploadItem
from .offline_image_models import OfflineImageMetadata


class ImageUploadItemSerializer(serializers.ModelSerializer):
    """Serializer for ImageUploadItem."""
    
    metadata_uuid = serializers.UUIDField(source='metadata.image_uuid', read_only=True)
    metadata_status = serializers.CharField(source='metadata.status', read_only=True)
    
    class Meta:
        model = ImageUploadItem
        fields = [
            'id',
            'sequence_number',
            'upload_status',
            'error_message',
            'metadata_uuid',
            'metadata_status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class ImageUploadSessionSerializer(serializers.ModelSerializer):
    """Serializer for ImageUploadSession."""
    
    upload_items = ImageUploadItemSerializer(many=True, read_only=True)
    progress_percentage = serializers.SerializerMethodField()
    is_complete = serializers.SerializerMethodField()
    radiology_order_id = serializers.IntegerField(source='radiology_order.id', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ImageUploadSession
        fields = [
            'id',
            'session_uuid',
            'radiology_order_id',
            'device_id',
            'device_info',
            'status',
            'total_images',
            'images_uploaded',
            'images_failed',
            'progress_percentage',
            'is_complete',
            'created_at',
            'started_at',
            'completed_at',
            'error_message',
            'created_by_name',
            'upload_items',
        ]
        read_only_fields = [
            'id',
            'status',
            'images_uploaded',
            'images_failed',
            'created_at',
            'started_at',
            'completed_at',
        ]
    
    def get_progress_percentage(self, obj):
        """Get upload progress as percentage."""
        return obj.get_progress_percentage()
    
    def get_is_complete(self, obj):
        """Check if session is complete."""
        return obj.is_complete()
    
    def get_created_by_name(self, obj):
        """Get creator's name."""
        if obj.created_by:
            return obj.created_by.get_full_name()
        return None


class ImageUploadSessionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating ImageUploadSession."""
    
    class Meta:
        model = ImageUploadSession
        fields = [
            'session_uuid',
            'radiology_order',
            'device_id',
            'device_info',
            'total_images',
        ]
    
    def validate_radiology_order(self, value):
        """Validate radiology order exists."""
        if not value:
            raise serializers.ValidationError("Radiology order is required.")
        return value


class BinaryUploadSerializer(serializers.Serializer):
    """Serializer for binary upload."""
    
    image_uuid = serializers.UUIDField(required=True)
    file = serializers.FileField(required=True)
    
    def validate_file(self, value):
        """Validate file size and type."""
        # Max file size: 100MB
        max_size = 100 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size exceeds maximum allowed size of {max_size / (1024*1024)}MB"
            )
        
        # Validate MIME type
        allowed_types = [
            'image/jpeg',
            'image/png',
            'image/dicom',
            'application/dicom',
            'application/octet-stream',  # For DICOM files
        ]
        
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                f"File type not allowed. Allowed types: {', '.join(allowed_types)}"
            )
        
        return value


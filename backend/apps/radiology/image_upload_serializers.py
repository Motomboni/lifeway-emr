"""
Serializers for Image Upload Session API.
"""
from rest_framework import serializers
from .image_upload_session_models import ImageUploadSession


class ImageUploadSessionSerializer(serializers.ModelSerializer):
    """Serializer for ImageUploadSession."""
    
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    actor_name = serializers.SerializerMethodField()
    radiology_order_id = serializers.IntegerField(source='radiology_order.id', read_only=True)
    
    class Meta:
        model = ImageUploadSession
        fields = [
            'session_id',
            'radiology_order_id',
            'file_name',
            'file_size',
            'content_type',
            'status',
            'status_display',
            'bytes_uploaded',
            'upload_progress_percent',
            'retry_count',
            'max_retries',
            'error_message',
            'error_code',
            'server_ack_received',
            'server_ack_at',
            'server_image_id',
            'metadata_uploaded',
            'metadata_uploaded_at',
            'binary_uploaded',
            'binary_uploaded_at',
            'actor_name',
            'created_at',
            'updated_at',
            'metadata',
        ]
        read_only_fields = fields
    
    def get_actor_name(self, obj):
        """Get actor's full name."""
        if obj.created_by:
            return obj.created_by.get_full_name()
        return None


class ImageUploadSessionCreateSerializer(serializers.Serializer):
    """Serializer for creating an upload session."""
    
    radiology_order_id = serializers.IntegerField()
    local_file_path = serializers.CharField(max_length=500)
    file_name = serializers.CharField(max_length=255)
    content_type = serializers.CharField(max_length=100)
    metadata = serializers.JSONField(required=False, default=dict)


class ImageUploadMetadataSerializer(serializers.Serializer):
    """Serializer for metadata upload response."""
    
    session_id = serializers.UUIDField()
    status = serializers.CharField()
    metadata_uploaded = serializers.BooleanField()
    next_step = serializers.CharField(required=False)


class ImageUploadBinarySerializer(serializers.Serializer):
    """Serializer for binary upload request."""
    
    resume_from = serializers.IntegerField(default=0, min_value=0)
    chunk_size = serializers.IntegerField(default=1048576, min_value=1024)  # 1MB default


class ImageUploadBinaryResponseSerializer(serializers.Serializer):
    """Serializer for binary upload response."""
    
    session_id = serializers.UUIDField()
    status = serializers.CharField()
    binary_uploaded = serializers.BooleanField()
    progress_percent = serializers.DecimalField(max_digits=5, decimal_places=2)
    image_id = serializers.IntegerField(required=False)


class ImageUploadAcknowledgeSerializer(serializers.Serializer):
    """Serializer for upload acknowledgment."""
    
    server_image_id = serializers.IntegerField()


class ImageUploadAcknowledgeResponseSerializer(serializers.Serializer):
    """Serializer for acknowledgment response."""
    
    session_id = serializers.UUIDField()
    status = serializers.CharField()
    ack_received = serializers.BooleanField()
    safe_to_delete_local = serializers.BooleanField()


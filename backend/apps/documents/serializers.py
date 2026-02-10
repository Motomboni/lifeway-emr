"""
Serializers for document models.
"""
from rest_framework import serializers
from .models import MedicalDocument


class MedicalDocumentSerializer(serializers.ModelSerializer):
    """Serializer for Medical Documents."""
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    file_url = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    
    class Meta:
        model = MedicalDocument
        fields = [
            'id',
            'visit',
            'document_type',
            'title',
            'description',
            'file',
            'file_url',
            'file_name',
            'file_size',
            'mime_type',
            'uploaded_by',
            'uploaded_by_name',
            'is_deleted',
            'deleted_at',
            'deleted_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'uploaded_by',
            'file_size',
            'mime_type',
            'is_deleted',
            'deleted_at',
            'deleted_by',
            'created_at',
            'updated_at',
        ]
    
    def get_file_url(self, obj):
        """Get file URL."""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None
    
    def get_file_name(self, obj):
        """Get file name."""
        if obj.file:
            return obj.file.name.split('/')[-1]
        return None


class MedicalDocumentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Medical Documents."""
    
    class Meta:
        model = MedicalDocument
        fields = [
            'document_type',
            'title',
            'description',
            'file',
        ]

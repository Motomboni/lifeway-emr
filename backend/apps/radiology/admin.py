"""
Django Admin configuration for Radiology models.
"""
from django.contrib import admin
from .models import RadiologyRequest, RadiologyOrder, RadiologyResult
from .offline_image_models import OfflineImageMetadata
from .pacs_lite_models import RadiologyStudy, RadiologySeries, RadiologyImage
from .image_upload_session_models import ImageUploadSession


@admin.register(RadiologyRequest)
class RadiologyRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'visit', 'consultation', 'study_type', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['study_type', 'study_code', 'clinical_indication']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['visit', 'consultation', 'ordered_by', 'reported_by']


@admin.register(RadiologyOrder)
class RadiologyOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'visit', 'imaging_type', 'body_part', 'status', 'ordered_by', 'created_at']
    list_filter = ['status', 'imaging_type', 'priority', 'created_at']
    search_fields = ['body_part', 'clinical_indication']
    readonly_fields = ['created_at']
    raw_id_fields = ['visit', 'ordered_by']


@admin.register(RadiologyResult)
class RadiologyResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'radiology_order', 'finding_flag', 'reported_by', 'reported_at']
    list_filter = ['finding_flag', 'reported_at']
    search_fields = ['report']
    readonly_fields = ['reported_at']
    raw_id_fields = ['radiology_order', 'reported_by']


@admin.register(OfflineImageMetadata)
class OfflineImageMetadataAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'image_uuid',
        'radiology_order',
        'filename',
        'file_size',
        'status',
        'created_at',
        'ack_received_at',
        'retry_count',
    ]
    list_filter = ['status', 'mime_type', 'created_at', 'ack_received_at']
    search_fields = ['image_uuid', 'filename', 'checksum']
    readonly_fields = [
        'image_uuid',
        'created_at',
        'metadata_uploaded_at',
        'binary_uploaded_at',
        'ack_received_at',
        'failed_at',
        'retry_count',
        'last_retry_at',
    ]
    raw_id_fields = ['radiology_order']
    
    fieldsets = (
        ('Image Information', {
            'fields': ('image_uuid', 'radiology_order', 'filename', 'file_size', 'mime_type', 'checksum')
        }),
        ('Metadata', {
            'fields': ('image_metadata',)
        }),
        ('Upload Status', {
            'fields': (
                'status',
                'metadata_uploaded_at',
                'binary_uploaded_at',
                'ack_received_at',
                'failed_at',
                'failure_reason',
            )
        }),
        ('Retry Information', {
            'fields': ('retry_count', 'last_retry_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )


@admin.register(RadiologyStudy)
class RadiologyStudyAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'study_uid',
        'radiology_order',
        'study_description',
        'modality',
        'study_date',
        'patient_name',
        'created_at',
    ]
    list_filter = ['modality', 'study_date', 'created_at']
    search_fields = ['study_uid', 'study_description', 'patient_name', 'patient_id']
    readonly_fields = ['study_uid', 'created_at', 'updated_at']
    raw_id_fields = ['radiology_order']


@admin.register(RadiologySeries)
class RadiologySeriesAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'series_uid',
        'study',
        'series_number',
        'series_description',
        'modality',
        'created_at',
    ]
    list_filter = ['modality', 'created_at']
    search_fields = ['series_uid', 'series_description']
    readonly_fields = ['series_uid', 'created_at', 'updated_at']
    raw_id_fields = ['study']


@admin.register(RadiologyImage)
class RadiologyImageAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'image_uid',
        'study_uid',
        'series_uid',
        'filename',
        'file_key',
        'instance_number',
        'uploaded_by',
        'uploaded_at',
    ]
    list_filter = ['mime_type', 'uploaded_at', 'validated_at']
    search_fields = ['image_uid', 'file_key', 'filename', 'checksum']
    readonly_fields = [
        'image_uid',
        'file_key',
        'checksum',
        'image_metadata',
        'uploaded_by',
        'uploaded_at',
        'validated_at',
    ]
    raw_id_fields = ['series', 'offline_metadata', 'uploaded_by']
    
    def study_uid(self, obj):
        return obj.series.study.study_uid if obj.series and obj.series.study else None
    study_uid.short_description = 'Study UID'
    
    def series_uid(self, obj):
        return obj.series.series_uid if obj.series else None
    series_uid.short_description = 'Series UID'


@admin.register(ImageUploadSession)
class ImageUploadSessionAdmin(admin.ModelAdmin):
    """
    Admin interface for Image Upload Sessions.
    
    Read-only for most fields to maintain audit trail integrity.
    """
    list_display = [
        'session_id',
        'radiology_order',
        'file_name',
        'file_size',
        'status',
        'upload_progress_percent',
        'retry_count',
        'server_ack_received',
        'created_at',
    ]
    list_filter = [
        'status',
        'content_type',
        'server_ack_received',
        'metadata_uploaded',
        'binary_uploaded',
        'created_at',
    ]
    search_fields = [
        'session_id',
        'local_file_uuid',
        'file_name',
        'checksum',
        'radiology_order__id',
    ]
    readonly_fields = [
        'session_id',
        'local_file_uuid',
        'radiology_order',
        'local_file_path',
        'file_name',
        'file_size',
        'content_type',
        'checksum',
        'bytes_uploaded',
        'upload_progress_percent',
        'retry_count',
        'max_retries',
        'last_retry_at',
        'error_message',
        'error_code',
        'server_ack_received',
        'server_ack_at',
        'server_image_id',
        'metadata_uploaded',
        'metadata_uploaded_at',
        'binary_uploaded',
        'binary_uploaded_at',
        'created_by',
        'created_at',
        'updated_at',
    ]
    raw_id_fields = ['radiology_order', 'created_by']
    
    fieldsets = (
        ('Session Information', {
            'fields': ('session_id', 'local_file_uuid', 'radiology_order', 'created_by')
        }),
        ('File Information', {
            'fields': ('local_file_path', 'file_name', 'file_size', 'content_type', 'checksum')
        }),
        ('Upload Status', {
            'fields': (
                'status',
                'bytes_uploaded',
                'upload_progress_percent',
                'metadata_uploaded',
                'metadata_uploaded_at',
                'binary_uploaded',
                'binary_uploaded_at',
            )
        }),
        ('Server Acknowledgment', {
            'fields': (
                'server_ack_received',
                'server_ack_at',
                'server_image_id',
            )
        }),
        ('Retry Information', {
            'fields': ('retry_count', 'max_retries', 'last_retry_at')
        }),
        ('Error Information', {
            'fields': ('error_message', 'error_code')
        }),
        ('Metadata', {
            'fields': ('metadata',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def has_add_permission(self, request):
        """Prevent manual creation of upload sessions."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion to maintain audit trail."""
        return False


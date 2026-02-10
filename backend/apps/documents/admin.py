"""
Django admin configuration for document models.
"""
from django.contrib import admin
from .models import MedicalDocument


@admin.register(MedicalDocument)
class MedicalDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'document_type', 'visit', 'uploaded_by', 'file_size', 'created_at', 'is_deleted']
    list_filter = ['document_type', 'is_deleted', 'created_at']
    search_fields = ['title', 'description', 'visit__patient__first_name', 'visit__patient__last_name']
    readonly_fields = ['file_size', 'mime_type', 'created_at', 'updated_at', 'deleted_at']
    fieldsets = (
        ('Document Information', {
            'fields': ('visit', 'document_type', 'title', 'description')
        }),
        ('File', {
            'fields': ('file', 'file_size', 'mime_type')
        }),
        ('Metadata', {
            'fields': ('uploaded_by', 'created_at', 'updated_at')
        }),
        ('Soft Delete', {
            'fields': ('is_deleted', 'deleted_at', 'deleted_by')
        }),
    )

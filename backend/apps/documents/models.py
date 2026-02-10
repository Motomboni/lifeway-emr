"""
Document models for storing medical documents, images, and reports.
"""
from django.db import models
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
import os


def document_upload_path(instance, filename):
    """Generate upload path for documents."""
    # Organize by visit_id for easier management
    visit_id = instance.visit_id if instance.visit_id else 'general'
    return f'documents/visit_{visit_id}/{filename}'


class MedicalDocument(models.Model):
    """
    Medical document storage - visit-scoped document management.
    
    Per EMR Rules:
    - Visit-scoped: Documents belong to a visit
    - PHI protection: Documents contain sensitive patient data
    - Audit logging: All document access logged
    - Immutability: Documents cannot be deleted (soft-delete only)
    """
    DOCUMENT_TYPES = [
        ('LAB_REPORT', 'Lab Report'),
        ('RADIOLOGY_REPORT', 'Radiology Report'),
        ('CONSULTATION_NOTE', 'Consultation Note'),
        ('PRESCRIPTION', 'Prescription'),
        ('REFERRAL_LETTER', 'Referral Letter'),
        ('DISCHARGE_SUMMARY', 'Discharge Summary'),
        ('CONSENT_FORM', 'Consent Form'),
        ('INSURANCE_CARD', 'Insurance Card'),
        ('ID_DOCUMENT', 'ID Document'),
        ('OTHER', 'Other'),
    ]
    
    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.CASCADE,
        related_name='documents',
        help_text="Visit this document belongs to"
    )
    
    document_type = models.CharField(
        max_length=50,
        choices=DOCUMENT_TYPES,
        help_text="Type of medical document"
    )
    
    title = models.CharField(
        max_length=200,
        help_text="Document title/name"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Document description or notes"
    )
    
    file = models.FileField(
        upload_to=document_upload_path,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'tiff', 'dcm']
            )
        ],
        help_text="Document file"
    )
    
    file_size = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="File size in bytes"
    )
    
    mime_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="MIME type of the file"
    )
    
    uploaded_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='documents_uploaded',
        help_text="User who uploaded this document"
    )
    
    is_deleted = models.BooleanField(
        default=False,
        help_text="Soft delete flag - documents cannot be permanently deleted"
    )
    
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When document was soft-deleted"
    )
    
    deleted_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents_deleted',
        help_text="User who deleted this document"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'medical_documents'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['visit', '-created_at']),
            models.Index(fields=['document_type', 'is_deleted']),
            models.Index(fields=['uploaded_by']),
        ]
        verbose_name = 'Medical Document'
        verbose_name_plural = 'Medical Documents'
    
    def __str__(self):
        return f"{self.title} ({self.get_document_type_display()}) - Visit {self.visit_id}"
    
    def save(self, *args, **kwargs):
        """Calculate file size and MIME type on save."""
        if self.file:
            self.file_size = self.file.size
            # Try to determine MIME type from extension
            ext = os.path.splitext(self.file.name)[1].lower()
            mime_types = {
                '.pdf': 'application/pdf',
                '.doc': 'application/msword',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.tiff': 'image/tiff',
                '.dcm': 'application/dicom',
            }
            self.mime_type = mime_types.get(ext, 'application/octet-stream')
        super().save(*args, **kwargs)
    
    def soft_delete(self, user):
        """Soft delete document (cannot be permanently deleted per EMR rules)."""
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])

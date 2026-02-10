"""
Invoice and Receipt Models for Document Tracking

Per EMR Rules:
- Sequential numbering for invoices and receipts
- Document storage and history
- Append-only (no deletions)
- QR codes for verification
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal


class InvoiceReceipt(models.Model):
    """
    Unified model for tracking both Invoices and Receipts.
    
    Design Principles:
    1. Sequential numbering per document type
    2. Immutable once created (append-only)
    3. QR code for verification
    4. PDF storage for audit trail
    """
    
    DOCUMENT_TYPE_CHOICES = [
        ('RECEIPT', 'Receipt'),
        ('INVOICE', 'Invoice'),
        ('STATEMENT', 'Billing Statement'),
    ]
    
    # Document identification
    document_type = models.CharField(
        max_length=20,
        choices=DOCUMENT_TYPE_CHOICES,
        help_text="Type of document (RECEIPT, INVOICE, STATEMENT)"
    )
    
    document_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Sequential document number (e.g., REC-0001, INV-0001)"
    )
    
    # Relationships
    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.PROTECT,
        related_name='invoice_receipts',
        help_text="Visit this document belongs to"
    )
    
    payment = models.ForeignKey(
        'billing.Payment',
        on_delete=models.PROTECT,
        related_name='invoice_receipts',
        null=True,
        blank=True,
        help_text="Payment this receipt is for (if applicable)"
    )
    
    # Document data (stored as JSON for flexibility)
    document_data = models.JSONField(
        help_text="Complete document data (charges, payments, etc.)"
    )
    
    # PDF storage
    pdf_file = models.FileField(
        upload_to='invoices_receipts/%Y/%m/',
        null=True,
        blank=True,
        help_text="Generated PDF file"
    )
    
    # QR code for verification
    qr_code_data = models.TextField(
        blank=True,
        help_text="QR code data for document verification"
    )
    
    # Metadata
    generated_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='generated_documents',
        help_text="User who generated this document"
    )
    
    generated_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this document was generated"
    )
    
    # Email/SMS tracking
    emailed_to = models.EmailField(
        blank=True,
        null=True,
        help_text="Email address document was sent to"
    )
    
    sms_sent_to = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Phone number SMS was sent to"
    )
    
    emailed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When document was emailed"
    )
    
    sms_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When SMS was sent"
    )
    
    class Meta:
        db_table = 'invoice_receipts'
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['document_type', 'document_number']),
            models.Index(fields=['visit', 'document_type']),
            models.Index(fields=['generated_at']),
        ]
    
    def __str__(self):
        return f"{self.document_type} {self.document_number} - Visit #{self.visit.id}"
    
    def clean(self):
        """Validate document data."""
        if self.document_type == 'RECEIPT' and not self.payment:
            # Receipts can be generated without specific payment (for all payments)
            pass
        if self.document_type == 'INVOICE':
            # Invoices don't have payments
            if self.payment:
                raise ValidationError("Invoices should not have associated payments.")
    
    def save(self, *args, **kwargs):
        """Ensure document is immutable after creation."""
        if self.pk:
            # Check if any critical fields are being changed
            original = InvoiceReceipt.objects.get(pk=self.pk)
            if original.document_number != self.document_number:
                raise ValidationError("Document number cannot be changed.")
            if original.document_type != self.document_type:
                raise ValidationError("Document type cannot be changed.")
            if original.visit_id != self.visit_id:
                raise ValidationError("Visit cannot be changed.")
        
        self.full_clean()
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Prevent deletion - append-only records."""
        raise ValidationError("Invoice/Receipt records cannot be deleted. They are append-only for audit purposes.")


class DocumentNumberSequence(models.Model):
    """
    Tracks sequential numbering for invoices and receipts.
    
    Separate sequences for:
    - Receipts (REC-0001, REC-0002, ...)
    - Invoices (INV-0001, INV-0002, ...)
    - Statements (STMT-0001, STMT-0002, ...)
    """
    
    DOCUMENT_TYPE_CHOICES = [
        ('RECEIPT', 'Receipt'),
        ('INVOICE', 'Invoice'),
        ('STATEMENT', 'Billing Statement'),
    ]
    
    document_type = models.CharField(
        max_length=20,
        choices=DOCUMENT_TYPE_CHOICES,
        unique=True,
        help_text="Type of document"
    )
    
    current_number = models.IntegerField(
        default=0,
        help_text="Current sequence number"
    )
    
    prefix = models.CharField(
        max_length=10,
        help_text="Prefix for document number (e.g., REC, INV)"
    )
    
    year = models.IntegerField(
        help_text="Year for this sequence (allows yearly reset)"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last update timestamp"
    )
    
    class Meta:
        db_table = 'document_number_sequences'
        unique_together = [['document_type', 'year']]
    
    def __str__(self):
        return f"{self.document_type} {self.prefix}-{self.current_number:04d} ({self.year})"
    
    @classmethod
    def get_next_number(cls, document_type: str) -> str:
        """
        Get next sequential number for a document type.
        
        Returns format: PREFIX-YYYY-NNNN (e.g., REC-2026-0001)
        """
        from datetime import datetime
        
        current_year = datetime.now().year
        
        # Get or create sequence for this document type and year
        sequence, created = cls.objects.get_or_create(
            document_type=document_type,
            year=current_year,
            defaults={
                'current_number': 0,
                'prefix': cls._get_prefix(document_type),
            }
        )
        
        # Increment and save
        sequence.current_number += 1
        sequence.save()
        
        # Format: PREFIX-YYYY-NNNN
        return f"{sequence.prefix}-{current_year}-{sequence.current_number:04d}"
    
    @staticmethod
    def _get_prefix(document_type: str) -> str:
        """Get prefix for document type."""
        prefixes = {
            'RECEIPT': 'REC',
            'INVOICE': 'INV',
            'STATEMENT': 'STMT',
        }
        return prefixes.get(document_type, 'DOC')


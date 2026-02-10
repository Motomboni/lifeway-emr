# Modern Invoicing and Receipting System

## Overview

A robust, modern invoicing and receipting system with PDF generation, sequential numbering, QR codes, and document tracking.

## Features

### ✅ Implemented

1. **Sequential Numbering System**
   - Receipts: `REC-YYYY-NNNN` (e.g., REC-2026-0001)
   - Invoices: `INV-YYYY-NNNN` (e.g., INV-2026-0001)
   - Statements: `STMT-YYYY-NNNN`
   - Yearly reset for clean numbering

2. **PDF Generation**
   - Professional PDF templates using WeasyPrint
   - QR codes for document verification
   - Modern, clean design
   - Print-ready formatting

3. **Document Tracking**
   - `InvoiceReceipt` model for all generated documents
   - Immutable records (append-only)
   - PDF file storage
   - Email/SMS tracking fields

4. **API Endpoints**
   - `GET /api/v1/visits/{visit_id}/billing/receipt/?format=pdf` - PDF receipt
   - `GET /api/v1/visits/{visit_id}/billing/receipt/` - JSON receipt data
   - `GET /api/v1/visits/{visit_id}/billing/invoice/?format=pdf` - PDF invoice
   - `GET /api/v1/visits/{visit_id}/billing/invoice/` - JSON invoice data

## Installation

### Required Packages

**Core (Required):**
```bash
pip install qrcode[pil]
```

**PDF Generation (Optional - Windows users may skip):**
```bash
pip install weasyprint
```

**Note for Windows Users:**
WeasyPrint requires GTK+ libraries which are complex to install on Windows. The system works perfectly without PDF generation - it will return JSON data instead. PDF generation is optional and gracefully handled if WeasyPrint is not available.

**Alternative PDF Libraries for Windows:**
- `reportlab` - Pure Python, no system dependencies
- `xhtml2pdf` - HTML to PDF, easier Windows installation

### Database Migration

```bash
python manage.py makemigrations billing
python manage.py migrate billing
```

## Usage

### Backend

#### Generate Receipt (JSON)
```python
from apps.billing.receipt_service import ReceiptService

receipt_data = ReceiptService.generate_receipt(visit)
```

#### Generate Receipt (PDF)
```python
receipt_data, pdf_bytes = ReceiptService.generate_receipt_with_pdf(visit, user=request.user)
```

#### Generate Invoice (PDF)
```python
invoice_data, pdf_bytes = ReceiptService.generate_invoice_with_pdf(visit, user=request.user)
```

### Frontend

#### Download PDF Receipt
```typescript
const response = await fetch(
  `/api/v1/visits/${visitId}/billing/receipt/?format=pdf`,
  {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  }
);
const blob = await response.blob();
// Download or display PDF
```

## Models

### InvoiceReceipt
- Tracks all generated documents
- Stores PDF files
- QR code data
- Email/SMS tracking
- Immutable (no deletions)

### DocumentNumberSequence
- Manages sequential numbering
- Yearly sequences
- Thread-safe increments

## Next Steps

### TODO

1. **Frontend Components**
   - [ ] Modern Invoice/Receipt viewer component
   - [ ] Print functionality
   - [ ] Download buttons
   - [ ] Document history panel
   - [ ] Email/SMS sending UI

2. **Email/SMS Integration**
   - [ ] Email service integration
   - [ ] SMS service integration
   - [ ] Template customization
   - [ ] Delivery tracking

3. **Settings**
   - [ ] Clinic information settings
   - [ ] Logo upload
   - [ ] Custom templates
   - [ ] Email/SMS configuration

4. **Advanced Features**
   - [ ] Digital signatures
   - [ ] Multi-language support
   - [ ] Custom branding
   - [ ] Batch generation

## Configuration

### Settings

Add to `settings.py`:

```python
# Clinic Information
CLINIC_NAME = "Lifeway Medical Centre Ltd"
CLINIC_ADDRESS = "123 Medical Street, Lagos, Nigeria"
CLINIC_PHONE = "+234-XXX-XXXX"
CLINIC_EMAIL = "info@clinic.com"
```

## QR Code Verification

QR codes contain:
- Document type (RECEIPT/INVOICE)
- Document number
- Visit ID

Format: `RECEIPT:REC-2026-0001:VISIT:123`

## File Structure

```
backend/apps/billing/
├── invoice_receipt_models.py    # Document tracking models
├── pdf_service.py                # PDF generation service
├── receipt_service.py            # Enhanced receipt service
└── receipt_views.py              # Updated views with PDF support
```

## Notes

- **PDF generation is optional** - The system works perfectly without WeasyPrint installed
- If PDF generation is not available, the API returns JSON data instead
- All documents are stored for audit purposes (even without PDF)
- Sequential numbering resets yearly for clean records
- Windows users: WeasyPrint requires GTK+ libraries. Consider using `reportlab` or `xhtml2pdf` as alternatives, or use JSON format which works perfectly for frontend PDF generation
- The system gracefully handles missing WeasyPrint - no errors, just JSON responses


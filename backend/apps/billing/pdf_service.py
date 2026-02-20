"""
PDF Generation Service for Invoices and Receipts

Uses WeasyPrint for HTML to PDF conversion.
Modern, professional PDF generation with QR codes.
"""
import io
import logging
import sys
import qrcode
from django.conf import settings

_logger = logging.getLogger(__name__)
from decimal import Decimal
from pathlib import Path
from typing import Dict, Any, Optional
from django.core.files.base import ContentFile
from django.utils import timezone
from datetime import datetime

# Suppress WeasyPrint's own "could not import external libraries" message when GTK is missing
try:
    from contextlib import redirect_stderr
    _devnull = io.StringIO()
    with redirect_stderr(_devnull):
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError) as e:
    # WeasyPrint not available or system dependencies missing
    WEASYPRINT_AVAILABLE = False
    HTML = None
    CSS = None
    FontConfiguration = None
    # Store error for informative messages
    WEASYPRINT_ERROR = str(e)


class PDFService:
    """
    Service for generating PDF documents from HTML templates.
    """
    
    @staticmethod
    def generate_qr_code(data: str) -> str:
        """
        Generate QR code as base64 encoded image.
        
        Args:
            data: Data to encode in QR code
            
        Returns:
            Base64 encoded image string
        """
        import base64
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    @staticmethod
    def format_currency(amount: str | Decimal | float) -> str:
        """Format amount as Nigerian Naira."""
        if isinstance(amount, str):
            amount = Decimal(amount)
        elif isinstance(amount, float):
            amount = Decimal(str(amount))
        
        return f"₦{amount:,.2f}"
    
    @staticmethod
    def format_date(date_str: str) -> str:
        """Format ISO date string to readable format."""
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%d %B %Y, %I:%M %p')
        except (ValueError, TypeError):
            return date_str
    
    @staticmethod
    def generate_receipt_pdf(receipt_data: Dict[str, Any], format_type: str = 'a4') -> bytes:
        """
        Generate PDF receipt from receipt data.
        
        Args:
            receipt_data: Receipt data dictionary
            
        Returns:
            PDF bytes
            
        Raises:
            ImportError: If WeasyPrint is not available
        """
        if not WEASYPRINT_AVAILABLE:
            error_msg = "WeasyPrint is not available."
            if 'WEASYPRINT_ERROR' in globals():
                error_msg += f" Error: {WEASYPRINT_ERROR}"
            error_msg += "\nFor Windows: WeasyPrint requires GTK+ libraries. Consider using reportlab or xhtml2pdf instead."
            raise ImportError(error_msg)
        
        # Generate QR code
        qr_data = f"RECEIPT:{receipt_data.get('receipt_number')}:VISIT:{receipt_data.get('visit_id')}"
        qr_code_img = PDFService.generate_qr_code(qr_data)
        
        # Get clinic info from settings or use defaults
        clinic_name = getattr(settings, 'CLINIC_NAME', 'Lifeway Medical Centre Ltd')
        clinic_address = getattr(settings, 'CLINIC_ADDRESS', 'Plot 1593, ZONE E, APO RESETTLEMENT, ABUJA')
        clinic_phone = getattr(settings, 'CLINIC_PHONE', '07058893439, 08033145080, 08033114417')
        clinic_email = getattr(settings, 'CLINIC_EMAIL', 'info@clinic.com')
        
        # Build HTML based on format
        if format_type.lower() == 'pos':
            html_content = PDFService._build_receipt_html_pos(
                receipt_data, qr_code_img, clinic_name, clinic_address, clinic_phone, clinic_email
            )
        else:
            html_content = PDFService._build_receipt_html(
                receipt_data, qr_code_img, clinic_name, clinic_address, clinic_phone, clinic_email
            )
        
        # Get logo path for base_url (helps WeasyPrint resolve images from disk)
        logo_path = PDFService._get_logo_path()
        base_url = None
        if logo_path:
            # Use file:// URL for logo directory so WeasyPrint can load logo.png reliably on Windows
            logo_dir = Path(logo_path).resolve().parent
            base_url = logo_dir.as_uri() + '/'
            if getattr(settings, 'DEBUG', False):
                _logger.debug("Receipt PDF: Using base_url=%s for logo.png", base_url)
        else:
            if getattr(settings, 'DEBUG', False):
                _logger.debug("Receipt PDF: No logo path found, base_url=None")
        
        # Generate PDF with base_url so <img src="logo.png"> resolves
        html = HTML(string=html_content, base_url=base_url)
        pdf_bytes = html.write_pdf()
        
        return pdf_bytes
    
    @staticmethod
    def generate_invoice_pdf(invoice_data: Dict[str, Any], format_type: str = 'a4') -> bytes:
        """
        Generate PDF invoice from invoice data.
        
        Args:
            invoice_data: Invoice data dictionary
            
        Returns:
            PDF bytes
            
        Raises:
            ImportError: If WeasyPrint is not available
        """
        if not WEASYPRINT_AVAILABLE:
            error_msg = "WeasyPrint is not available."
            if 'WEASYPRINT_ERROR' in globals():
                error_msg += f" Error: {WEASYPRINT_ERROR}"
            error_msg += "\nFor Windows: WeasyPrint requires GTK+ libraries. Consider using reportlab or xhtml2pdf instead."
            raise ImportError(error_msg)
        
        # Generate QR code
        qr_data = f"INVOICE:{invoice_data.get('invoice_number')}:VISIT:{invoice_data.get('visit_id')}"
        qr_code_img = PDFService.generate_qr_code(qr_data)
        
        # Get clinic info
        clinic_name = getattr(settings, 'CLINIC_NAME', 'Lifeway Medical Centre Ltd')
        clinic_address = getattr(settings, 'CLINIC_ADDRESS', 'Plot 1593, ZONE E, APO RESETTLEMENT, ABUJA')
        clinic_phone = getattr(settings, 'CLINIC_PHONE', '07058893439, 08033145080, 08033114417')
        clinic_email = getattr(settings, 'CLINIC_EMAIL', 'info@clinic.com')
        
        # Build HTML based on format
        if format_type.lower() == 'pos':
            html_content = PDFService._build_invoice_html_pos(
                invoice_data, qr_code_img, clinic_name, clinic_address, clinic_phone, clinic_email
            )
        else:
            html_content = PDFService._build_invoice_html(
                invoice_data, qr_code_img, clinic_name, clinic_address, clinic_phone, clinic_email
            )
        
        # Get logo path for base_url (helps WeasyPrint resolve images from disk)
        logo_path = PDFService._get_logo_path()
        base_url = None
        if logo_path:
            # Use file:// URL for logo directory so WeasyPrint can load logo.png reliably on Windows
            logo_dir = Path(logo_path).resolve().parent
            base_url = logo_dir.as_uri() + '/'
            if getattr(settings, 'DEBUG', False):
                _logger.debug("Invoice PDF: Using base_url=%s for logo.png", base_url)
        else:
            if getattr(settings, 'DEBUG', False):
                _logger.debug("Invoice PDF: No logo path found, base_url=None")
        
        # Generate PDF with base_url so <img src="logo.png"> resolves
        html = HTML(string=html_content, base_url=base_url)
        pdf_bytes = html.write_pdf()
        
        return pdf_bytes
    
    @staticmethod
    def _get_logo_path() -> Optional[str]:
        """
        Get logo file path for WeasyPrint.
        """
        import os
        from django.conf import settings
        from pathlib import Path
        
        # Try to get logo path from settings
        logo_path = getattr(settings, 'CLINIC_LOGO_PATH', None)
        
        # Get BASE_DIR from settings
        BASE_DIR = getattr(settings, 'BASE_DIR', None)
        
        # Current file location for relative path calculation
        current_file = Path(__file__).resolve()
        current_dir = current_file.parent  # backend/apps/billing/
        
        # Try multiple possible paths (in order of preference)
        possible_paths = []
        
        # 1. Path from settings (most specific)
        if logo_path:
            possible_paths.append(str(logo_path))
        
        # 2. Relative to current file (most reliable)
        # pdf_service.py is in: backend/apps/billing/
        # logo.png is in: frontend/public/
        # Need to go up to project root: parent.parent.parent = backend/ -> go up one more
        project_root_from_file = current_dir.parent.parent.parent  # This gets us to project root
        relative_logo = project_root_from_file / 'frontend' / 'public' / 'logo.png'
        possible_paths.append(str(relative_logo))
        
        # 3. Using BASE_DIR from settings
        if BASE_DIR:
            base_dir_logo = Path(BASE_DIR) / 'frontend' / 'public' / 'logo.png'
            possible_paths.append(str(base_dir_logo))
        
        # 4. Current working directory (might be project root)
        cwd_logo = Path(os.getcwd()) / 'frontend' / 'public' / 'logo.png'
        possible_paths.append(str(cwd_logo))
        
        # 5. One level up from BASE_DIR (in case BASE_DIR is backend/)
        if BASE_DIR:
            parent_logo = Path(BASE_DIR).parent / 'frontend' / 'public' / 'logo.png'
            possible_paths.append(str(parent_logo))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_paths = []
        for path in possible_paths:
            normalized = os.path.normpath(path) if path else None
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique_paths.append(normalized)
        
        if getattr(settings, 'DEBUG', False):
            _logger.debug("Looking for logo. Trying %s paths... Current file: %s BASE_DIR: %s", len(unique_paths), current_file, BASE_DIR)
        
        # Try each path
        for path in unique_paths:
            exists = os.path.exists(path)
            if getattr(settings, 'DEBUG', False):
                _logger.debug("Checking: %s -> %s", path, 'EXISTS' if exists else 'NOT FOUND')
            if exists:
                try:
                    size = os.path.getsize(path)
                    if size == 0:
                        if getattr(settings, 'DEBUG', False):
                            _logger.debug("Logo file is empty: %s", path)
                        continue
                    
                    abs_path = os.path.abspath(path)
                    if getattr(settings, 'DEBUG', False):
                        _logger.debug("LOGO FOUND: %s (%s bytes)", abs_path, size)
                    return abs_path
                except Exception as e:
                    _logger.warning("Failed to process logo from %s: %s", path, e)
                    continue
        
        if getattr(settings, 'DEBUG', False):
            _logger.debug("LOGO NOT FOUND after trying all %s paths", len(unique_paths))
        return None
    
    @staticmethod
    def _get_logo_base64() -> Optional[str]:
        """
        Get logo as base64 encoded string for embedding in HTML.
        This is the most reliable method for WeasyPrint.
        """
        import base64
        
        logo_path = PDFService._get_logo_path()
        if not logo_path:
            if getattr(settings, 'DEBUG', False):
                _logger.debug("_get_logo_base64: No logo path returned from _get_logo_path()")
            return None
        
        if getattr(settings, 'DEBUG', False):
            _logger.debug("_get_logo_base64: Converting logo to base64 from: %s", logo_path)
        
        try:
            with open(logo_path, 'rb') as f:
                logo_data = f.read()
                if getattr(settings, 'DEBUG', False):
                    _logger.debug("_get_logo_base64: Read %s bytes from logo file", len(logo_data))
                
                if len(logo_data) == 0:
                    if getattr(settings, 'DEBUG', False):
                        _logger.debug("_get_logo_base64: Logo file is empty: %s", logo_path)
                    return None
                
                logo_base64 = base64.b64encode(logo_data).decode('utf-8')
                
                # Detect image type and return data URI
                if logo_path.lower().endswith('.png'):
                    result = f"data:image/png;base64,{logo_base64}"
                    return result
                elif logo_path.lower().endswith('.jpg') or logo_path.lower().endswith('.jpeg'):
                    result = f"data:image/jpeg;base64,{logo_base64}"
                    return result
                elif logo_path.lower().endswith('.gif'):
                    result = f"data:image/gif;base64,{logo_base64}"
                    return result
                else:
                    result = f"data:image/png;base64,{logo_base64}"
                    return result
                    
        except FileNotFoundError:
            _logger.warning("_get_logo_base64: File not found: %s", logo_path)
            return None
        except PermissionError:
            _logger.warning("_get_logo_base64: Permission denied reading: %s", logo_path)
            return None
        except Exception as e:
            _logger.warning("_get_logo_base64: Failed to encode logo: %s", e)
            return None
    
    @staticmethod
    def _build_receipt_html(
        receipt_data: Dict[str, Any],
        qr_code_img: str,
        clinic_name: str,
        clinic_address: str,
        clinic_phone: str,
        clinic_email: str
    ) -> str:
        """Build HTML content for receipt."""
        
        charges = receipt_data.get('charges', [])
        payments = receipt_data.get('payments', [])
        
        charges_html = ""
        for charge in charges:
            charges_html += f"""
            <tr>
                <td>{charge.get('category', 'N/A')}</td>
                <td>{charge.get('description', '')}</td>
                <td style="text-align: right;">{PDFService.format_currency(charge.get('amount', '0'))}</td>
            </tr>
            """
        
        payments_html = ""
        for payment in payments:
            payments_html += f"""
            <tr>
                <td>{PDFService.format_date(payment.get('created_at', ''))}</td>
                <td>{payment.get('payment_method', 'N/A')}</td>
                <td>{payment.get('transaction_reference', 'N/A')}</td>
                <td style="text-align: right;">{PDFService.format_currency(payment.get('amount', '0'))}</td>
            </tr>
            """
        
        # Use relative path logo.png so WeasyPrint loads it via base_url (file://) - reliable on Windows
        logo_path = PDFService._get_logo_path()
        if logo_path:
            logo_html = '<div class="logo-container"><img src="logo.png" alt="Lifeway Medical Centre Ltd Logo" style="max-height: 80px; max-width: 200px; margin-bottom: 10px; display: block; margin-left: auto; margin-right: auto;" /></div>'
        else:
            logo_html = ''
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Receipt {receipt_data.get('receipt_number', '')}</title>
    <style>
        @page {{
            size: A4;
            margin: 20mm;
        }}
        body {{
            font-family: 'Arial', sans-serif;
            font-size: 12px;
            color: #333;
            line-height: 1.6;
        }}
        .header {{
            border-bottom: 3px solid #2563eb;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .clinic-info {{
            text-align: center;
            margin-bottom: 20px;
        }}
        .logo-container {{
            margin-bottom: 15px;
        }}
        .clinic-name {{
            font-size: 24px;
            font-weight: bold;
            color: #2563eb;
            margin-bottom: 10px;
        }}
        .document-title {{
            font-size: 18px;
            font-weight: bold;
            text-align: center;
            margin: 20px 0;
            color: #1e40af;
        }}
        .receipt-number {{
            text-align: right;
            font-size: 14px;
            color: #666;
            margin-bottom: 20px;
        }}
        .info-section {{
            margin-bottom: 30px;
        }}
        .info-row {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            padding: 8px 0;
            border-bottom: 1px solid #e5e7eb;
        }}
        .info-label {{
            font-weight: bold;
            color: #555;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th {{
            background-color: #2563eb;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: bold;
        }}
        td {{
            padding: 10px;
            border-bottom: 1px solid #e5e7eb;
        }}
        .total-row {{
            font-weight: bold;
            background-color: #f3f4f6;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e5e7eb;
            display: flex;
            justify-content: space-between;
        }}
        .qr-code {{
            text-align: center;
        }}
        .qr-code img {{
            width: 120px;
            height: 120px;
        }}
        .thank-you {{
            text-align: center;
            font-size: 14px;
            color: #2563eb;
            margin-top: 30px;
            font-style: italic;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="clinic-info">
            {logo_html}
            <div class="clinic-name">{clinic_name}</div>
            <div>{clinic_address}</div>
            <div>Phone: {clinic_phone} | Email: {clinic_email}</div>
        </div>
        <div class="document-title">PAYMENT RECEIPT</div>
        <div class="receipt-number">Receipt No: {receipt_data.get('receipt_number', 'N/A')}</div>
    </div>
    
    <div class="info-section">
        <div class="info-row">
            <span class="info-label">Patient Name:</span>
            <span>{receipt_data.get('patient_name', 'N/A')}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Patient ID:</span>
            <span>{receipt_data.get('patient_id', 'N/A')}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Visit ID:</span>
            <span>#{receipt_data.get('visit_id', 'N/A')}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Date:</span>
            <span>{PDFService.format_date(receipt_data.get('date', ''))}</span>
        </div>
    </div>
    
    <h3>Charges</h3>
    <table>
        <thead>
            <tr>
                <th>Category</th>
                <th>Description</th>
                <th style="text-align: right;">Amount</th>
            </tr>
        </thead>
        <tbody>
            {charges_html}
            <tr class="total-row">
                <td colspan="2">Total Charges</td>
                <td style="text-align: right;">{PDFService.format_currency(receipt_data.get('total_charges', '0'))}</td>
            </tr>
        </tbody>
    </table>
    
    <h3>Payments</h3>
    <table>
        <thead>
            <tr>
                <th>Date</th>
                <th>Method</th>
                <th>Reference</th>
                <th style="text-align: right;">Amount</th>
            </tr>
        </thead>
        <tbody>
            {payments_html}
            <tr class="total-row">
                <td colspan="3">Total Paid</td>
                <td style="text-align: right;">{PDFService.format_currency(receipt_data.get('total_paid', '0'))}</td>
            </tr>
        </tbody>
    </table>
    
    <div class="info-section">
        <div class="info-row">
            <span class="info-label">Outstanding Balance:</span>
            <span style="font-weight: bold; color: {'#dc2626' if Decimal(receipt_data.get('outstanding_balance', '0')) > 0 else '#16a34a'};">
                {PDFService.format_currency(receipt_data.get('outstanding_balance', '0'))}
            </span>
        </div>
    </div>
    
    <div class="footer">
        <div class="qr-code">
            <div>Verify Receipt</div>
            <img src="{qr_code_img}" alt="QR Code">
        </div>
        <div style="text-align: right;">
            <div style="margin-top: 60px;">
                <div style="border-top: 1px solid #333; width: 200px; margin-left: auto;">
                    Authorized Signature
                </div>
            </div>
        </div>
    </div>
    
    <div class="thank-you">
        Thank you for your payment!
    </div>
</body>
</html>
        """
    
    @staticmethod
    def _build_invoice_html(
        invoice_data: Dict[str, Any],
        qr_code_img: str,
        clinic_name: str,
        clinic_address: str,
        clinic_phone: str,
        clinic_email: str
    ) -> str:
        """Build HTML content for invoice."""
        
        charges = invoice_data.get('charges', [])
        
        charges_html = ""
        for charge in charges:
            charges_html += f"""
            <tr>
                <td>{charge.get('category', 'N/A')}</td>
                <td>{charge.get('description', '')}</td>
                <td style="text-align: right;">{PDFService.format_currency(charge.get('amount', '0'))}</td>
            </tr>
            """
        
        # Use relative path logo.png so WeasyPrint loads it via base_url (file://)
        logo_path = PDFService._get_logo_path()
        if logo_path:
            logo_html = '<div class="logo-container"><img src="logo.png" alt="Lifeway Medical Centre Ltd Logo" style="max-height: 80px; max-width: 200px; margin-bottom: 10px; display: block; margin-left: auto; margin-right: auto;" /></div>'
        else:
            logo_html = ''
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Invoice {invoice_data.get('invoice_number', '')}</title>
    <style>
        @page {{
            size: A4;
            margin: 20mm;
        }}
        body {{
            font-family: 'Arial', sans-serif;
            font-size: 12px;
            color: #333;
            line-height: 1.6;
        }}
        .header {{
            border-bottom: 3px solid #2563eb;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .clinic-info {{
            text-align: center;
            margin-bottom: 20px;
        }}
        .logo-container {{
            margin-bottom: 15px;
        }}
        .clinic-name {{
            font-size: 24px;
            font-weight: bold;
            color: #2563eb;
            margin-bottom: 10px;
        }}
        .document-title {{
            font-size: 18px;
            font-weight: bold;
            text-align: center;
            margin: 20px 0;
            color: #1e40af;
        }}
        .invoice-number {{
            text-align: right;
            font-size: 14px;
            color: #666;
            margin-bottom: 20px;
        }}
        .info-section {{
            margin-bottom: 30px;
        }}
        .info-row {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            padding: 8px 0;
            border-bottom: 1px solid #e5e7eb;
        }}
        .info-label {{
            font-weight: bold;
            color: #555;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th {{
            background-color: #2563eb;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: bold;
        }}
        td {{
            padding: 10px;
            border-bottom: 1px solid #e5e7eb;
        }}
        .total-row {{
            font-weight: bold;
            background-color: #f3f4f6;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e5e7eb;
            display: flex;
            justify-content: space-between;
        }}
        .qr-code {{
            text-align: center;
        }}
        .qr-code img {{
            width: 120px;
            height: 120px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="clinic-info">
            {logo_html}
            <div class="clinic-name">{clinic_name}</div>
            <div>{clinic_address}</div>
            <div>Phone: {clinic_phone} | Email: {clinic_email}</div>
        </div>
        <div class="document-title">INVOICE</div>
        <div class="invoice-number">Invoice No: {invoice_data.get('invoice_number', 'N/A')}</div>
    </div>
    
    <div class="info-section">
        <div class="info-row">
            <span class="info-label">Patient Name:</span>
            <span>{invoice_data.get('patient_name', 'N/A')}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Patient ID:</span>
            <span>{invoice_data.get('patient_id', 'N/A')}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Insurance Provider:</span>
            <span>{invoice_data.get('insurance_provider', 'N/A')}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Insurance Number:</span>
            <span>{invoice_data.get('insurance_number', 'N/A')}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Visit ID:</span>
            <span>#{invoice_data.get('visit_id', 'N/A')}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Date:</span>
            <span>{PDFService.format_date(invoice_data.get('date', ''))}</span>
        </div>
    </div>
    
    <h3>Services Rendered</h3>
    <table>
        <thead>
            <tr>
                <th>Category</th>
                <th>Description</th>
                <th style="text-align: right;">Amount</th>
            </tr>
        </thead>
        <tbody>
            {charges_html}
            <tr class="total-row">
                <td colspan="2">Total Charges</td>
                <td style="text-align: right;">{PDFService.format_currency(invoice_data.get('total_charges', '0'))}</td>
            </tr>
        </tbody>
    </table>
    
    <div class="info-section">
        <div class="info-row">
            <span class="info-label">Insurance Coverage:</span>
            <span>{PDFService.format_currency(invoice_data.get('insurance_amount', '0'))}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Patient Payable:</span>
            <span style="font-weight: bold;">{PDFService.format_currency(invoice_data.get('patient_payable', '0'))}</span>
        </div>
    </div>
    
    <div class="footer">
        <div class="qr-code">
            <div>Verify Invoice</div>
            <img src="{qr_code_img}" alt="QR Code">
        </div>
        <div style="text-align: right;">
            <div style="margin-top: 60px;">
                <div style="border-top: 1px solid #333; width: 200px; margin-left: auto;">
                    Authorized Signature
                </div>
            </div>
        </div>
    </div>
</body>
</html>
        """
    
    @staticmethod
    def _build_receipt_html_pos(
        receipt_data: Dict[str, Any],
        qr_code_img: str,
        clinic_name: str,
        clinic_address: str,
        clinic_phone: str,
        clinic_email: str
    ) -> str:
        """Build POS-friendly HTML content for receipt (58mm/80mm width)."""
        
        charges = receipt_data.get('charges', [])
        payments = receipt_data.get('payments', [])
        
        # Build charges list
        charges_text = ""
        for charge in charges:
            desc = charge.get('description', '')[:30]  # Truncate long descriptions
            amount = PDFService.format_currency(charge.get('amount', '0'))
            charges_text += f"""
            <div style="display: flex; justify-content: space-between; margin: 4px 0; font-size: 9px;">
                <span>{desc}</span>
                <span>{amount}</span>
            </div>
            """
        
        # Build payments list
        payments_text = ""
        for payment in payments:
            method = payment.get('payment_method', 'N/A')[:15]
            amount = PDFService.format_currency(payment.get('amount', '0'))
            payments_text += f"""
            <div style="display: flex; justify-content: space-between; margin: 4px 0; font-size: 9px;">
                <span>{method}</span>
                <span>{amount}</span>
            </div>
            """
        
        # Use relative path logo.png so WeasyPrint loads it via base_url (file://)
        logo_path = PDFService._get_logo_path()
        if logo_path:
            logo_html = '<div class="logo-container"><img src="logo.png" alt="Lifeway Medical Centre Ltd Logo" style="max-height: 40px; max-width: 120px; margin-bottom: 5px; display: block; margin-left: auto; margin-right: auto;" /></div>'
        else:
            logo_html = ''
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Receipt {receipt_data.get('receipt_number', '')}</title>
    <style>
        @page {{
            size: 80mm auto;
            margin: 5mm;
        }}
        body {{
            font-family: 'Courier New', monospace;
            font-size: 10px;
            color: #000;
            line-height: 1.3;
            margin: 0;
            padding: 0;
        }}
        .header {{
            text-align: center;
            margin-bottom: 10px;
            border-bottom: 1px dashed #000;
            padding-bottom: 8px;
        }}
        .logo-container {{
            margin-bottom: 5px;
        }}
        .clinic-name {{
            font-size: 12px;
            font-weight: bold;
            margin-bottom: 4px;
        }}
        .clinic-details {{
            font-size: 8px;
            margin: 2px 0;
        }}
        .title {{
            font-size: 11px;
            font-weight: bold;
            text-align: center;
            margin: 8px 0;
        }}
        .receipt-number {{
            font-size: 9px;
            text-align: center;
            margin: 4px 0;
        }}
        .section {{
            margin: 8px 0;
            border-top: 1px dashed #000;
            padding-top: 6px;
        }}
        .section-title {{
            font-size: 10px;
            font-weight: bold;
            margin-bottom: 4px;
        }}
        .info-line {{
            display: flex;
            justify-content: space-between;
            margin: 3px 0;
            font-size: 9px;
        }}
        .label {{
            font-weight: bold;
        }}
        .divider {{
            border-top: 1px dashed #000;
            margin: 6px 0;
        }}
        .total {{
            font-weight: bold;
            font-size: 10px;
        }}
        .footer {{
            text-align: center;
            margin-top: 10px;
            padding-top: 8px;
            border-top: 1px dashed #000;
            font-size: 8px;
        }}
        .qr-code {{
            text-align: center;
            margin: 8px 0;
        }}
        .qr-code img {{
            width: 60px;
            height: 60px;
        }}
    </style>
</head>
<body>
    <div class="header">
        {logo_html}
        <div class="clinic-name">{clinic_name}</div>
        <div class="clinic-details">{clinic_address}</div>
        <div class="clinic-details">{clinic_phone}</div>
    </div>
    
    <div class="title">PAYMENT RECEIPT</div>
    <div class="receipt-number">Receipt No: {receipt_data.get('receipt_number', 'N/A')}</div>
    
    <div class="divider"></div>
    
    <div class="info-line">
        <span class="label">Patient:</span>
        <span>{receipt_data.get('patient_name', 'N/A')[:25]}</span>
    </div>
    <div class="info-line">
        <span class="label">Patient ID:</span>
        <span>{receipt_data.get('patient_id', 'N/A')}</span>
    </div>
    <div class="info-line">
        <span class="label">Visit ID:</span>
        <span>#{receipt_data.get('visit_id', 'N/A')}</span>
    </div>
    <div class="info-line">
        <span class="label">Date:</span>
        <span>{PDFService.format_date(receipt_data.get('date', ''))[:20]}</span>
    </div>
    
    <div class="divider"></div>
    
    <div class="section">
        <div class="section-title">CHARGES</div>
        {charges_text}
        <div class="divider"></div>
        <div class="info-line total">
            <span>TOTAL CHARGES:</span>
            <span>{PDFService.format_currency(receipt_data.get('total_charges', '0'))}</span>
        </div>
    </div>
    
    <div class="section">
        <div class="section-title">PAYMENTS</div>
        {payments_text}
        <div class="divider"></div>
        <div class="info-line total">
            <span>TOTAL PAID:</span>
            <span>{PDFService.format_currency(receipt_data.get('total_paid', '0'))}</span>
        </div>
    </div>
    
    <div class="divider"></div>
    
    <div class="info-line total">
        <span>BALANCE:</span>
        <span>{PDFService.format_currency(receipt_data.get('outstanding_balance', '0'))}</span>
    </div>
    
    <div class="qr-code">
        <img src="{qr_code_img}" alt="QR Code">
        <div style="font-size: 7px;">Scan to verify</div>
    </div>
    
    <div class="footer">
        Thank you for your payment!
    </div>
</body>
</html>
        """
    
    @staticmethod
    def _build_invoice_html_pos(
        invoice_data: Dict[str, Any],
        qr_code_img: str,
        clinic_name: str,
        clinic_address: str,
        clinic_phone: str,
        clinic_email: str
    ) -> str:
        """Build POS-friendly HTML content for invoice (58mm/80mm width)."""
        
        charges = invoice_data.get('charges', [])
        
        # Build charges list
        charges_text = ""
        for charge in charges:
            desc = charge.get('description', '')[:30]  # Truncate long descriptions
            amount = PDFService.format_currency(charge.get('amount', '0'))
            charges_text += f"""
            <div style="display: flex; justify-content: space-between; margin: 4px 0; font-size: 9px;">
                <span>{desc}</span>
                <span>{amount}</span>
            </div>
            """
        
        # Use relative path logo.png so WeasyPrint loads it via base_url (file://)
        logo_path = PDFService._get_logo_path()
        if logo_path:
            logo_html = '<div class="logo-container"><img src="logo.png" alt="Lifeway Medical Centre Ltd Logo" style="max-height: 40px; max-width: 120px; margin-bottom: 5px; display: block; margin-left: auto; margin-right: auto;" /></div>'
        else:
            logo_html = ''
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Invoice {invoice_data.get('invoice_number', '')}</title>
    <style>
        @page {{
            size: 80mm auto;
            margin: 5mm;
        }}
        body {{
            font-family: 'Courier New', monospace;
            font-size: 10px;
            color: #000;
            line-height: 1.3;
            margin: 0;
            padding: 0;
        }}
        .header {{
            text-align: center;
            margin-bottom: 10px;
            border-bottom: 1px dashed #000;
            padding-bottom: 8px;
        }}
        .logo-container {{
            margin-bottom: 5px;
        }}
        .clinic-name {{
            font-size: 12px;
            font-weight: bold;
            margin-bottom: 4px;
        }}
        .clinic-details {{
            font-size: 8px;
            margin: 2px 0;
        }}
        .title {{
            font-size: 11px;
            font-weight: bold;
            text-align: center;
            margin: 8px 0;
        }}
        .invoice-number {{
            font-size: 9px;
            text-align: center;
            margin: 4px 0;
        }}
        .section {{
            margin: 8px 0;
            border-top: 1px dashed #000;
            padding-top: 6px;
        }}
        .section-title {{
            font-size: 10px;
            font-weight: bold;
            margin-bottom: 4px;
        }}
        .info-line {{
            display: flex;
            justify-content: space-between;
            margin: 3px 0;
            font-size: 9px;
        }}
        .label {{
            font-weight: bold;
        }}
        .divider {{
            border-top: 1px dashed #000;
            margin: 6px 0;
        }}
        .total {{
            font-weight: bold;
            font-size: 10px;
        }}
        .footer {{
            text-align: center;
            margin-top: 10px;
            padding-top: 8px;
            border-top: 1px dashed #000;
            font-size: 8px;
        }}
        .qr-code {{
            text-align: center;
            margin: 8px 0;
        }}
        .qr-code img {{
            width: 60px;
            height: 60px;
        }}
    </style>
</head>
<body>
    <div class="header">
        {logo_html}
        <div class="clinic-name">{clinic_name}</div>
        <div class="clinic-details">{clinic_address}</div>
        <div class="clinic-details">{clinic_phone}</div>
    </div>
    
    <div class="title">INVOICE</div>
    <div class="invoice-number">Invoice No: {invoice_data.get('invoice_number', 'N/A')}</div>
    
    <div class="divider"></div>
    
    <div class="info-line">
        <span class="label">Patient:</span>
        <span>{invoice_data.get('patient_name', 'N/A')[:25]}</span>
    </div>
    <div class="info-line">
        <span class="label">Patient ID:</span>
        <span>{invoice_data.get('patient_id', 'N/A')}</span>
    </div>
    <div class="info-line">
        <span class="label">Insurance:</span>
        <span>{invoice_data.get('insurance_provider', 'N/A')[:20]}</span>
    </div>
    <div class="info-line">
        <span class="label">Policy No:</span>
        <span>{invoice_data.get('insurance_number', 'N/A')[:15]}</span>
    </div>
    <div class="info-line">
        <span class="label">Visit ID:</span>
        <span>#{invoice_data.get('visit_id', 'N/A')}</span>
    </div>
    <div class="info-line">
        <span class="label">Date:</span>
        <span>{PDFService.format_date(invoice_data.get('date', ''))[:20]}</span>
    </div>
    
    <div class="divider"></div>
    
    <div class="section">
        <div class="section-title">CHARGES</div>
        {charges_text}
        <div class="divider"></div>
        <div class="info-line total">
            <span>TOTAL CHARGES:</span>
            <span>{PDFService.format_currency(invoice_data.get('total_charges', '0'))}</span>
        </div>
    </div>
    
    <div class="divider"></div>
    
    <div class="info-line">
        <span class="label">Insurance:</span>
        <span>{PDFService.format_currency(invoice_data.get('insurance_amount', '0'))}</span>
    </div>
    <div class="info-line total">
        <span>PATIENT PAYABLE:</span>
        <span>{PDFService.format_currency(invoice_data.get('patient_payable', '0'))}</span>
    </div>
    <div class="info-line total">
        <span>BALANCE:</span>
        <span>{PDFService.format_currency(invoice_data.get('outstanding_balance', '0'))}</span>
    </div>
    
    <div class="qr-code">
        <img src="{qr_code_img}" alt="QR Code">
        <div style="font-size: 7px;">Scan to verify</div>
    </div>
    
    <div class="footer">
        Submit to insurance provider
    </div>
</body>
</html>
        """


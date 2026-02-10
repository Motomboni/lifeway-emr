"""
Email Service for Sending Invoices and Receipts

Per EMR Rules:
- Receipts/Invoices can be emailed to patients
- Email sending is logged for audit
- PDF attachment is included
"""
import logging
from typing import Optional
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class EmailService:
    """
    Service for sending invoices and receipts via email.
    """
    
    @staticmethod
    def send_receipt_email(
        receipt_data: dict,
        email_address: str,
        pdf_bytes: Optional[bytes] = None
    ) -> bool:
        """
        Send receipt via email.
        
        Args:
            receipt_data: Receipt data dictionary
            email_address: Recipient email address
            pdf_bytes: Optional PDF bytes to attach
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            subject = f"Payment Receipt - {receipt_data.get('receipt_number', 'N/A')}"
            
            # Create email body
            body = f"""
Dear {receipt_data.get('patient_name', 'Patient')},

Please find attached your payment receipt for Visit #{receipt_data.get('visit_id', 'N/A')}.

Receipt Number: {receipt_data.get('receipt_number', 'N/A')}
Date: {receipt_data.get('date', 'N/A')}
Total Paid: {receipt_data.get('total_paid', '0')}

Thank you for your payment.

Best regards,
{receipt_data.get('clinic_name', 'Clinic')}
{receipt_data.get('clinic_phone', '')}
            """.strip()
            
            # Create email message
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@clinic.com'),
                to=[email_address],
            )
            
            # Attach PDF if available
            if pdf_bytes:
                email.attach(
                    f"receipt_{receipt_data.get('receipt_number', 'N/A')}.pdf",
                    pdf_bytes,
                    'application/pdf'
                )
            
            # Send email
            email.send()
            
            logger.info(f"Receipt email sent to {email_address} for visit {receipt_data.get('visit_id')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send receipt email to {email_address}: {str(e)}")
            return False
    
    @staticmethod
    def send_invoice_email(
        invoice_data: dict,
        email_address: str,
        pdf_bytes: Optional[bytes] = None
    ) -> bool:
        """
        Send invoice via email.
        
        Args:
            invoice_data: Invoice data dictionary
            email_address: Recipient email address
            pdf_bytes: Optional PDF bytes to attach
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            subject = f"Invoice - {invoice_data.get('invoice_number', 'N/A')}"
            
            # Create email body
            body = f"""
Dear {invoice_data.get('patient_name', 'Patient')},

Please find attached your invoice for Visit #{invoice_data.get('visit_id', 'N/A')}.

Invoice Number: {invoice_data.get('invoice_number', 'N/A')}
Date: {invoice_data.get('date', 'N/A')}
Insurance Provider: {invoice_data.get('insurance_provider', 'N/A')}
Total Charges: {invoice_data.get('total_charges', '0')}
Insurance Coverage: {invoice_data.get('insurance_amount', '0')}
Patient Payable: {invoice_data.get('patient_payable', '0')}

Please submit this invoice to your insurance provider.

Best regards,
{invoice_data.get('clinic_name', 'Clinic')}
{invoice_data.get('clinic_phone', '')}
            """.strip()
            
            # Create email message
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@clinic.com'),
                to=[email_address],
            )
            
            # Attach PDF if available
            if pdf_bytes:
                email.attach(
                    f"invoice_{invoice_data.get('invoice_number', 'N/A')}.pdf",
                    pdf_bytes,
                    'application/pdf'
                )
            
            # Send email
            email.send()
            
            logger.info(f"Invoice email sent to {email_address} for visit {invoice_data.get('visit_id')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send invoice email to {email_address}: {str(e)}")
            return False


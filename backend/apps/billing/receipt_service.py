"""
Receipt/Invoice Generation Service for Nigerian EMR.

Per EMR Rules:
- Receipts are generated for all payments
- Invoices are generated for insurance claims
- All financial records are append-only (no deletions)
- Receipts include visit-scoped charges and payments
- Sequential numbering for documents
- PDF generation with QR codes
"""
from decimal import Decimal
from typing import Dict, Any, List, Optional
from django.utils import timezone
from datetime import datetime
from django.core.files.base import ContentFile
from django.conf import settings

from .models import VisitCharge, Payment
from .billing_service import BillingService
from .insurance_models import VisitInsurance
from .invoice_receipt_models import InvoiceReceipt, DocumentNumberSequence
# PDFService imported lazily to avoid WeasyPrint import errors at startup


class ReceiptService:
    """
    Service for generating receipts and invoices.
    
    Receipt: Generated for patient payments (CASH, POS, TRANSFER, PAYSTACK, WALLET)
    Invoice: Generated for insurance/HMO claims
    """
    
    @staticmethod
    def generate_receipt(visit, payment: Optional[Payment] = None) -> Dict[str, Any]:
        """
        Generate a receipt for a visit payment.
        
        Args:
            visit: Visit instance
            payment: Optional Payment instance (if generating for specific payment)
        
        Returns:
            dict with receipt data:
                - receipt_number: Unique receipt number
                - visit_id: Visit ID
                - patient_name: Patient name
                - patient_id: Patient ID
                - date: Receipt date
                - charges: List of charges
                - payments: List of payments (or single payment if specified)
                - total_charges: Total charges
                - total_paid: Total paid
                - outstanding_balance: Outstanding balance
                - receipt_type: 'RECEIPT'
        """
        billing_summary = BillingService.compute_billing_summary(visit)
        
        # Get all charges
        charges = VisitCharge.objects.filter(visit=visit).order_by('created_at')
        charges_data = [
            {
                'category': charge.category,
                'description': charge.description,
                'amount': str(charge.amount),
                'created_at': charge.created_at.isoformat()
            }
            for charge in charges
        ]
        
        # Get payments
        if payment:
            payments_data = [{
                'id': payment.id,
                'amount': str(payment.amount),
                'payment_method': payment.payment_method,
                'transaction_reference': payment.transaction_reference,
                'notes': payment.notes,
                'processed_by': payment.processed_by.get_full_name() or str(payment.processed_by),
                'created_at': payment.created_at.isoformat()
            }]
        else:
            payments = Payment.objects.filter(visit=visit, status='CLEARED').order_by('created_at')
            payments_data = [
                {
                    'id': p.id,
                    'amount': str(p.amount),
                    'payment_method': p.payment_method,
                    'transaction_reference': p.transaction_reference,
                    'notes': p.notes,
                    'processed_by': p.processed_by.get_full_name() or str(p.processed_by),
                    'created_at': p.created_at.isoformat()
                }
                for p in payments
            ]
        
        # Generate sequential receipt number
        receipt_number = DocumentNumberSequence.get_next_number('RECEIPT')
        
        receipt_dict = {
            'receipt_number': receipt_number,
            'receipt_type': 'RECEIPT',
            'visit_id': visit.id,
            'patient_name': visit.patient.get_full_name() or str(visit.patient),
            'patient_id': visit.patient.patient_id,
            'date': timezone.now().isoformat(),
            'charges': charges_data,
            'payments': payments_data,
            'total_charges': str(billing_summary.total_charges),
            'total_paid': str(billing_summary.total_payments + billing_summary.total_wallet_debits),
            'outstanding_balance': str(billing_summary.outstanding_balance),
            'payment_status': billing_summary.payment_status,
            'clinic_name': getattr(settings, 'CLINIC_NAME', 'Lifeway Medical Centre Ltd'),
            'clinic_address': getattr(settings, 'CLINIC_ADDRESS', 'Plot 1593, ZONE E, APO RESETTLEMENT, ABUJA'),
            'clinic_phone': getattr(settings, 'CLINIC_PHONE', '07058893439, 08033145080, 08033114417'),
            'clinic_email': getattr(settings, 'CLINIC_EMAIL', 'info@clinic.com'),
        }
        
        return receipt_dict
    
    @staticmethod
    def generate_receipt_with_pdf(visit, payment: Optional[Payment] = None, user=None, format_type: str = 'a4') -> tuple:
        """
        Generate receipt data and PDF.
        
        Args:
            visit: Visit instance
            payment: Optional Payment instance
            user: User generating the receipt
            format_type: PDF format ('a4' or 'pos')
        
        Returns:
            tuple: (receipt_data dict, pdf_bytes)
        """
        receipt_data = ReceiptService.generate_receipt(visit, payment)
        
        # Lazy import to avoid WeasyPrint errors at startup
        try:
            print(f"[RECEIPT DEBUG] Generating PDF receipt (format={format_type})...")
            from .pdf_service import PDFService
            pdf_bytes = PDFService.generate_receipt_pdf(receipt_data, format_type=format_type)
            print(f"[RECEIPT DEBUG] PDF generated: {len(pdf_bytes)} bytes")
        except (ImportError, Exception) as e:
            # WeasyPrint not available or error, return empty bytes
            import logging
            import traceback
            logger = logging.getLogger(__name__)
            logger.warning(f"PDF generation failed: {e}")
            print(f"[RECEIPT DEBUG] PDF generation FAILED: {e}")
            traceback.print_exc()
            pdf_bytes = b''
        
        # Save to InvoiceReceipt model if user provided
        if user:
            try:
                invoice_receipt = InvoiceReceipt.objects.create(
                    document_type='RECEIPT',
                    document_number=receipt_data['receipt_number'],
                    visit=visit,
                    payment=payment,
                    document_data=receipt_data,
                    generated_by=user,
                    qr_code_data=f"RECEIPT:{receipt_data['receipt_number']}:VISIT:{visit.id}"
                )
                
                # Save PDF if generated
                if pdf_bytes:
                    invoice_receipt.pdf_file.save(
                        f"receipt_{receipt_data['receipt_number']}.pdf",
                        ContentFile(pdf_bytes),
                        save=True
                    )
            except Exception as e:
                # Log error but don't fail
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to save receipt to database: {e}")
        
        return receipt_data, pdf_bytes
    
    @staticmethod
    def generate_invoice(visit) -> Dict[str, Any]:
        """
        Generate an invoice for insurance/HMO claim.
        
        Args:
            visit: Visit instance with insurance
        
        Returns:
            dict with invoice data:
                - invoice_number: Unique invoice number
                - visit_id: Visit ID
                - patient_name: Patient name
                - patient_id: Patient ID
                - insurance_provider: HMO provider name
                - insurance_number: Patient insurance number
                - date: Invoice date
                - charges: List of charges
                - insurance_amount: Amount covered by insurance
                - patient_payable: Patient portion
                - invoice_type: 'INVOICE'
        """
        try:
            insurance = VisitInsurance.objects.select_related('provider').get(visit=visit)
        except VisitInsurance.DoesNotExist:
            raise ValueError("Visit does not have insurance. Cannot generate invoice.")
        
        # VisitInsurance uses FK 'provider' (not hmo_provider); policy number is 'policy_number'
        provider_name = 'N/A'
        if getattr(insurance, 'provider', None):
            provider_name = getattr(insurance.provider, 'name', 'N/A')
        policy_num = getattr(insurance, 'policy_number', '') or getattr(insurance, 'insurance_number', '')
        
        billing_summary = BillingService.compute_billing_summary(visit)
        
        # Get all charges
        charges = VisitCharge.objects.filter(visit=visit).order_by('created_at')
        charges_data = [
            {
                'category': charge.category,
                'description': charge.description,
                'amount': str(charge.amount),
                'created_at': charge.created_at.isoformat()
            }
            for charge in charges
        ]
        
        # Generate sequential invoice number
        invoice_number = DocumentNumberSequence.get_next_number('INVOICE')
        
        invoice_dict = {
            'invoice_number': invoice_number,
            'invoice_type': 'INVOICE',
            'visit_id': visit.id,
            'patient_name': visit.patient.get_full_name() or str(visit.patient),
            'patient_id': visit.patient.patient_id,
            'insurance_provider': provider_name,
            'insurance_number': policy_num,
            'approval_status': insurance.approval_status,
            'approved_amount': str(insurance.approved_amount) if insurance.approved_amount else None,
            'coverage_type': insurance.coverage_type,
            'coverage_percentage': insurance.coverage_percentage,
            'date': timezone.now().isoformat(),
            'charges': charges_data,
            'total_charges': str(billing_summary.total_charges),
            'insurance_amount': str(billing_summary.insurance_amount),
            'patient_payable': str(billing_summary.patient_payable),
            'outstanding_balance': str(billing_summary.outstanding_balance),
            'payment_status': billing_summary.payment_status,
            'clinic_name': getattr(settings, 'CLINIC_NAME', 'Lifeway Medical Centre Ltd'),
            'clinic_address': getattr(settings, 'CLINIC_ADDRESS', 'Plot 1593, ZONE E, APO RESETTLEMENT, ABUJA'),
            'clinic_phone': getattr(settings, 'CLINIC_PHONE', '07058893439, 08033145080, 08033114417'),
            'clinic_email': getattr(settings, 'CLINIC_EMAIL', 'info@clinic.com'),
        }
        
        return invoice_dict
    
    @staticmethod
    def generate_invoice_with_pdf(visit, user=None, format_type: str = 'a4') -> tuple:
        """
        Generate invoice data and PDF.
        
        Args:
            visit: Visit instance
            user: User generating the invoice
            format_type: PDF format ('a4' or 'pos')
        
        Returns:
            tuple: (invoice_data dict, pdf_bytes)
        """
        invoice_data = ReceiptService.generate_invoice(visit)
        
        # Lazy import to avoid WeasyPrint errors at startup
        try:
            from .pdf_service import PDFService
            pdf_bytes = PDFService.generate_invoice_pdf(invoice_data, format_type=format_type)
        except (ImportError, Exception) as e:
            # WeasyPrint not available or error, return empty bytes
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"PDF generation failed: {e}")
            pdf_bytes = b''
        
        # Save to InvoiceReceipt model if user provided
        if user:
            try:
                invoice_receipt = InvoiceReceipt.objects.create(
                    document_type='INVOICE',
                    document_number=invoice_data['invoice_number'],
                    visit=visit,
                    payment=None,  # Invoices don't have payments
                    document_data=invoice_data,
                    generated_by=user,
                    qr_code_data=f"INVOICE:{invoice_data['invoice_number']}:VISIT:{visit.id}"
                )
                
                # Save PDF if generated
                if pdf_bytes:
                    invoice_receipt.pdf_file.save(
                        f"invoice_{invoice_data['invoice_number']}.pdf",
                        ContentFile(pdf_bytes),
                        save=True
                    )
            except Exception as e:
                # Log error but don't fail
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to save invoice to database: {e}")
        
        return invoice_data, pdf_bytes
    
    @staticmethod
    def generate_billing_statement(visit) -> Dict[str, Any]:
        """
        Generate a complete billing statement for a visit.
        
        Includes all charges, payments, insurance, and wallet transactions.
        
        Args:
            visit: Visit instance
        
        Returns:
            dict with complete billing statement
        """
        billing_summary = BillingService.compute_billing_summary(visit)
        
        # Get all charges
        charges = VisitCharge.objects.filter(visit=visit).order_by('created_at')
        charges_data = [
            {
                'id': charge.id,
                'category': charge.category,
                'description': charge.description,
                'amount': str(charge.amount),
                'created_at': charge.created_at.isoformat()
            }
            for charge in charges
        ]
        
        # Get all payments
        payments = Payment.objects.filter(visit=visit).order_by('created_at')
        payments_data = [
            {
                'id': p.id,
                'amount': str(p.amount),
                'payment_method': p.payment_method,
                'status': p.status,
                'transaction_reference': p.transaction_reference,
                'notes': p.notes,
                'processed_by': p.processed_by.get_full_name() or str(p.processed_by),
                'created_at': p.created_at.isoformat()
            }
            for p in payments
        ]
        
        # Get wallet transactions
        from apps.wallet.models import WalletTransaction
        wallet_transactions = WalletTransaction.objects.filter(
            visit=visit,
            transaction_type='DEBIT'
        ).order_by('created_at')
        wallet_data = [
            {
                'id': wt.id,
                'amount': str(wt.amount),
                'status': wt.status,
                'created_at': wt.created_at.isoformat()
            }
            for wt in wallet_transactions
        ]
        
        # Get insurance info
        insurance_data = None
        try:
            insurance = VisitInsurance.objects.select_related('provider').get(visit=visit)
            prov = getattr(insurance, 'provider', None)
            provider_name = getattr(prov, 'name', 'N/A') if prov else 'N/A'
            policy_num = getattr(insurance, 'policy_number', '') or getattr(insurance, 'insurance_number', '')
            insurance_data = {
                'provider': provider_name,
                'insurance_number': policy_num,
                'approval_status': insurance.approval_status,
                'approved_amount': str(insurance.approved_amount) if insurance.approved_amount else None,
                'coverage_type': insurance.coverage_type,
                'coverage_percentage': insurance.coverage_percentage,
            }
        except VisitInsurance.DoesNotExist:
            pass
        
        return {
            'statement_number': f"STMT-{visit.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
            'visit_id': visit.id,
            'patient_name': visit.patient.get_full_name() or str(visit.patient),
            'patient_id': visit.patient.patient_id,
            'date': timezone.now().isoformat(),
            'charges': charges_data,
            'payments': payments_data,
            'wallet_transactions': wallet_data,
            'insurance': insurance_data,
            'summary': billing_summary.to_dict(),
            'clinic_name': getattr(settings, 'CLINIC_NAME', 'Lifeway Medical Centre Ltd'),
            'clinic_address': getattr(settings, 'CLINIC_ADDRESS', 'Apo Resettlement, Abuja'),
            'clinic_phone': getattr(settings, 'CLINIC_PHONE', '+234-XXX-XXXX'),
            'clinic_email': getattr(settings, 'CLINIC_EMAIL', 'info@clinic.com'),
        }


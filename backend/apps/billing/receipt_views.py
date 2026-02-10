"""
Receipt/Invoice API endpoints.

Per EMR Rules:
- Receipts are generated for all payments
- Invoices are generated for insurance claims
- Only Receptionist can generate receipts/invoices
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, ValidationError as DRFValidationError
from rest_framework.decorators import api_view

import logging
import os
from pathlib import Path
from django.conf import settings
from apps.visits.models import Visit
from .permissions import CanProcessPayment
from core.audit import AuditLog
from .receipt_service import ReceiptService
from .models import Payment
from .email_service import EmailService
from .invoice_receipt_models import InvoiceReceipt
from .pdf_service import PDFService

logger = logging.getLogger(__name__)


class ReceiptView(APIView):
    """
    GET /api/v1/visits/{visit_id}/billing/receipt/
    POST /api/v1/visits/{visit_id}/billing/receipt/
    
    Generate receipt for a visit payment.
    """
    permission_classes = [IsAuthenticated, CanProcessPayment]
    
    def get_visit(self, visit_id):
        """Get visit and verify access (select_related patient for receipt data)."""
        try:
            visit = Visit.objects.select_related('patient').get(id=visit_id)
        except Visit.DoesNotExist:
            raise NotFound("Visit not found.")
        
        return visit
    
    def get(self, request, visit_id):
        """Generate receipt for all payments on a visit."""
        from django.http import HttpResponse
        
        visit = self.get_visit(visit_id)
        
        # Check if PDF is requested
        format_type = request.query_params.get('format', 'json').lower()
        pdf_format = request.query_params.get('pdf_format', 'a4').lower()  # 'a4' or 'pos'
        
        if format_type == 'pdf':
            # Generate PDF
            receipt_data, pdf_bytes = ReceiptService.generate_receipt_with_pdf(
                visit, payment=None, user=request.user, format_type=pdf_format
            )
            
            if not pdf_bytes:
                return Response(
                    {'detail': 'PDF generation not available. Install WeasyPrint: pip install weasyprint'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            # Audit log
            user_role = getattr(request.user, 'role', None) or \
                       getattr(request.user, 'get_role', lambda: None)()
            AuditLog.log(
                user=request.user,
                role=user_role,
                action="RECEIPT_GENERATED",
                visit_id=visit.id,
                resource_type="receipt",
                resource_id=None,
                request=request
            )
            
            # Return PDF response
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="receipt_{receipt_data["receipt_number"]}.pdf"'
            return response
        else:
            # Return JSON
            receipt_data = ReceiptService.generate_receipt(visit)
            
            # Audit log
            user_role = getattr(request.user, 'role', None) or \
                       getattr(request.user, 'get_role', lambda: None)()
            AuditLog.log(
                user=request.user,
                role=user_role,
                action="RECEIPT_GENERATED",
                visit_id=visit.id,
                resource_type="receipt",
                resource_id=None,
                request=request
            )
            
            return Response(receipt_data, status=status.HTTP_200_OK)
    
    def post(self, request, visit_id):
        """Generate receipt for a specific payment."""
        visit = self.get_visit(visit_id)
        
        payment_id = request.data.get('payment_id')
        if not payment_id:
            raise DRFValidationError("payment_id is required.")
        
        try:
            payment = Payment.objects.get(id=payment_id, visit=visit)
        except Payment.DoesNotExist:
            raise NotFound("Payment not found.")
        
        receipt_data = ReceiptService.generate_receipt(visit, payment=payment)
        
        # Audit log
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        AuditLog.log(
            user=request.user,
            role=user_role,
            action="RECEIPT_GENERATED",
            visit_id=visit.id,
            resource_type="receipt",
            resource_id=payment.id,
            request=request
        )
        
        return Response(receipt_data, status=status.HTTP_200_OK)


class InvoiceView(APIView):
    """
    GET /api/v1/visits/{visit_id}/billing/invoice/
    
    Generate invoice for insurance/HMO claim.
    """
    permission_classes = [IsAuthenticated, CanProcessPayment]
    
    def get_visit(self, visit_id):
        """Get visit and verify access (select_related patient for receipt data)."""
        try:
            visit = Visit.objects.select_related('patient').get(id=visit_id)
        except Visit.DoesNotExist:
            raise NotFound("Visit not found.")
        
        return visit
    
    def get(self, request, visit_id):
        """Generate invoice for insurance claim."""
        from django.http import HttpResponse
        
        visit = self.get_visit(visit_id)
        
        # Check if PDF is requested
        format_type = request.query_params.get('format', 'json').lower()
        pdf_format = request.query_params.get('pdf_format', 'a4').lower()  # 'a4' or 'pos'
        
        try:
            if format_type == 'pdf':
                # Generate PDF
                invoice_data, pdf_bytes = ReceiptService.generate_invoice_with_pdf(
                    visit, user=request.user, format_type=pdf_format
                )
                
                if not pdf_bytes:
                    return Response(
                        {'detail': 'PDF generation not available. Install WeasyPrint: pip install weasyprint'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE
                    )
                
                # Audit log
                user_role = getattr(request.user, 'role', None) or \
                           getattr(request.user, 'get_role', lambda: None)()
                AuditLog.log(
                    user=request.user,
                    role=user_role,
                    action="INVOICE_GENERATED",
                    visit_id=visit.id,
                    resource_type="invoice",
                    resource_id=None,
                    request=request
                )
                
                # Return PDF response
                response = HttpResponse(pdf_bytes, content_type='application/pdf')
                response['Content-Disposition'] = f'inline; filename="invoice_{invoice_data["invoice_number"]}.pdf"'
                return response
            else:
                # Return JSON
                invoice_data = ReceiptService.generate_invoice(visit)
                
                # Audit log
                user_role = getattr(request.user, 'role', None) or \
                           getattr(request.user, 'get_role', lambda: None)()
                AuditLog.log(
                    user=request.user,
                    role=user_role,
                    action="INVOICE_GENERATED",
                    visit_id=visit.id,
                    resource_type="invoice",
                    resource_id=None,
                    request=request
                )
                
                return Response(invoice_data, status=status.HTTP_200_OK)
        except ValueError as e:
            raise DRFValidationError(str(e))
        except Exception as e:
            logger.error(f"Error generating invoice: {str(e)}", exc_info=True)
            raise DRFValidationError(f"Error generating invoice: {str(e)}")


@api_view(['GET'])
def test_logo_view(request):
    """
    Debug endpoint to test logo loading.
    GET /api/v1/visits/{visit_id}/billing/test-logo/
    """
    # Get BASE_DIR
    BASE_DIR = getattr(settings, 'BASE_DIR', None)
    logo_path = getattr(settings, 'CLINIC_LOGO_PATH', None)
    
    # Test logo loading
    logo_path = PDFService._get_logo_path()
    logo_base64 = PDFService._get_logo_base64() if logo_path else None
    
    # Build possible paths for debugging
    possible_paths = []
    if logo_path:
        possible_paths.append(str(logo_path))
    if BASE_DIR:
        possible_paths.append(str(Path(BASE_DIR) / 'frontend' / 'public' / 'logo.png'))
        possible_paths.append(str(Path(BASE_DIR).parent / 'frontend' / 'public' / 'logo.png'))
    
    # Check which paths exist
    path_status = {}
    for path in possible_paths:
        if path:
            exists = os.path.exists(path)
            path_status[path] = {
                'exists': exists,
                'size': os.path.getsize(path) if exists else 0
            }
    
    return Response({
        'logo_loaded': logo_base64 is not None,
        'logo_base64_length': len(logo_base64) if logo_base64 else 0,
        'base_dir': str(BASE_DIR) if BASE_DIR else None,
        'clinic_logo_path': logo_path,
        'path_status': path_status,
        'message': 'Logo loaded successfully' if logo_base64 else 'Logo not found - check paths above'
    }, status=status.HTTP_200_OK)


class BillingStatementView(APIView):
    """
    GET /api/v1/visits/{visit_id}/billing/statement/
    
    Generate complete billing statement for a visit.
    """
    permission_classes = [IsAuthenticated, CanProcessPayment]
    
    def get_visit(self, visit_id):
        """Get visit and verify access (select_related patient for receipt data)."""
        try:
            visit = Visit.objects.select_related('patient').get(id=visit_id)
        except Visit.DoesNotExist:
            raise NotFound("Visit not found.")
        
        return visit
    
    def get(self, request, visit_id):
        """Generate complete billing statement."""
        visit = self.get_visit(visit_id)
        
        statement_data = ReceiptService.generate_billing_statement(visit)
        
        # Audit log
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        AuditLog.log(
            user=request.user,
            role=user_role,
            action="BILLING_STATEMENT_GENERATED",
            visit_id=visit.id,
            resource_type="statement",
            resource_id=None,
            request=request
        )
        
        return Response(statement_data, status=status.HTTP_200_OK)


class SendReceiptEmailView(APIView):
    """
    POST /api/v1/visits/{visit_id}/billing/receipt/send-email/
    
    Send receipt via email.
    """
    permission_classes = [IsAuthenticated, CanProcessPayment]
    
    def get_visit(self, visit_id):
        """Get visit and verify access (select_related patient for receipt data)."""
        try:
            visit = Visit.objects.select_related('patient').get(id=visit_id)
        except Visit.DoesNotExist:
            raise NotFound("Visit not found.")
        
        return visit
    
    def post(self, request, visit_id):
        """Send receipt via email."""
        visit = self.get_visit(visit_id)
        
        email = request.data.get('email')
        if not email:
            raise DRFValidationError("email is required.")
        
        # Generate receipt data and PDF
        receipt_data, pdf_bytes = ReceiptService.generate_receipt_with_pdf(
            visit, payment=None, user=request.user
        )
        
        # Send email
        success = EmailService.send_receipt_email(receipt_data, email, pdf_bytes)
        
        if not success:
            return Response(
                {'detail': 'Failed to send email. Please check email configuration.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Update InvoiceReceipt record if exists
        try:
            invoice_receipt = InvoiceReceipt.objects.filter(
                visit=visit,
                document_type='RECEIPT',
                document_number=receipt_data['receipt_number']
            ).first()
            
            if invoice_receipt:
                from django.utils import timezone
                invoice_receipt.emailed_to = email
                invoice_receipt.emailed_at = timezone.now()
                invoice_receipt.save()
        except Exception as e:
            logger.warning(f"Failed to update email tracking: {e}")
        
        # Audit log
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        AuditLog.log(
            user=request.user,
            role=user_role,
            action="RECEIPT_EMAIL_SENT",
            visit_id=visit.id,
            resource_type="receipt",
            resource_id=None,
            request=request
        )
        
        return Response({
            'detail': f'Receipt sent to {email} successfully',
            'email': email,
        }, status=status.HTTP_200_OK)


class SendInvoiceEmailView(APIView):
    """
    POST /api/v1/visits/{visit_id}/billing/invoice/send-email/
    
    Send invoice via email.
    """
    permission_classes = [IsAuthenticated, CanProcessPayment]
    
    def get_visit(self, visit_id):
        """Get visit and verify access (select_related patient for receipt data)."""
        try:
            visit = Visit.objects.select_related('patient').get(id=visit_id)
        except Visit.DoesNotExist:
            raise NotFound("Visit not found.")
        
        return visit
    
    def post(self, request, visit_id):
        """Send invoice via email."""
        visit = self.get_visit(visit_id)
        
        email = request.data.get('email')
        if not email:
            raise DRFValidationError("email is required.")
        
        try:
            # Generate invoice data and PDF
            invoice_data, pdf_bytes = ReceiptService.generate_invoice_with_pdf(
                visit, user=request.user
            )
        except ValueError as e:
            raise DRFValidationError(str(e))
        
        # Send email
        success = EmailService.send_invoice_email(invoice_data, email, pdf_bytes)
        
        if not success:
            return Response(
                {'detail': 'Failed to send email. Please check email configuration.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Update InvoiceReceipt record if exists
        try:
            invoice_receipt = InvoiceReceipt.objects.filter(
                visit=visit,
                document_type='INVOICE',
                document_number=invoice_data['invoice_number']
            ).first()
            
            if invoice_receipt:
                from django.utils import timezone
                invoice_receipt.emailed_to = email
                invoice_receipt.emailed_at = timezone.now()
                invoice_receipt.save()
        except Exception as e:
            logger.warning(f"Failed to update email tracking: {e}")
        
        # Audit log
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        AuditLog.log(
            user=request.user,
            role=user_role,
            action="INVOICE_EMAIL_SENT",
            visit_id=visit.id,
            resource_type="invoice",
            resource_id=None,
            request=request
        )
        
        return Response({
            'detail': f'Invoice sent to {email} successfully',
            'email': email,
        }, status=status.HTTP_200_OK)


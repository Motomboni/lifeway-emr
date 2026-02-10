"""
Web-based service import from Excel files.

Allows Receptionists to upload Excel files and import services directly through the API.
"""
import pandas as pd
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import transaction
from decimal import Decimal, InvalidOperation
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError as DRFValidationError
from io import BytesIO

from apps.billing.price_lists import (
    LabServicePriceList,
    PharmacyServicePriceList,
    RadiologyServicePriceList,
    ProcedureServicePriceList,
)
from .permissions import CanProcessPayment
from core.audit import AuditLog

# Map department names to models
DEPARTMENT_MODELS = {
    'LAB': LabServicePriceList,
    'PHARMACY': PharmacyServicePriceList,
    'RADIOLOGY': RadiologyServicePriceList,
    'PROCEDURE': ProcedureServicePriceList,
}


class ImportServicesView(APIView):
    """
    POST /api/v1/billing/services/import/
    
    Upload and import services from Excel file.
    
    Request:
    - Content-Type: multipart/form-data
    - file: Excel file (.xlsx, .xls)
    - update: true/false (optional, default: false) - Update existing services
    - sheet: Sheet name or index (optional, default: first sheet)
    
    Response:
    {
        "success": true,
        "message": "Services imported successfully",
        "stats": {
            "total": 100,
            "created": 95,
            "updated": 5,
            "skipped": 0,
            "errors": []
        }
    }
    """
    permission_classes = [IsAuthenticated, CanProcessPayment]
    
    def post(self, request):
        """Import services from uploaded Excel file."""
        # Check if file was uploaded
        if 'file' not in request.FILES:
            raise DRFValidationError("No file uploaded. Please provide an Excel file.")
        
        uploaded_file = request.FILES['file']
        
        # Validate file extension
        file_name = uploaded_file.name.lower()
        valid_extensions = ['.xlsx', '.xls']
        if not any(file_name.endswith(ext) for ext in valid_extensions):
            raise DRFValidationError(
                f"Invalid file type. Please upload an Excel file (.xlsx or .xls). "
                f"Received: {uploaded_file.name}"
            )
        
        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if uploaded_file.size > max_size:
            raise DRFValidationError(
                f"File too large. Maximum size is 10MB. Received: {uploaded_file.size / 1024 / 1024:.2f}MB"
            )
        
        # Validate MIME type if available
        content_type = getattr(uploaded_file, 'content_type', '')
        valid_mime_types = [
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
            'application/vnd.ms-excel',  # .xls
            'application/octet-stream',  # Sometimes Excel files have this
        ]
        if content_type and content_type not in valid_mime_types:
            # Only warn if we have a content type, don't reject
            # Some systems don't set MIME type correctly
            pass
        
        # Get options
        update_existing = request.data.get('update', 'false').lower() == 'true'
        sheet = request.data.get('sheet', 0)
        
        # Read Excel file
        try:
            # Read file into memory
            file_content = uploaded_file.read()
            excel_file = BytesIO(file_content)
            
            # Read Excel using pandas
            df = pd.read_excel(excel_file, sheet_name=sheet)
        except Exception as e:
            raise DRFValidationError(f"Error reading Excel file: {str(e)}")
        
        # Normalize column names (case-insensitive, strip whitespace)
        df.columns = df.columns.str.strip().str.upper()
        
        # Required columns
        required_columns = ['DEPARTMENT', 'SERVICE CODE', 'SERVICE NAME', 'AMOUNT']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise DRFValidationError(
                f"Missing required columns: {', '.join(missing_columns)}\n"
                f"Found columns: {', '.join(df.columns)}\n"
                f"Required columns: Department, Service Code, Service Name, Amount"
            )
        
        # Validate and process data
        stats = {
            'total': len(df),
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': []
        }
        
        try:
            with transaction.atomic():
                for index, row in df.iterrows():
                    try:
                        # Extract data
                        department = str(row['DEPARTMENT']).strip().upper()
                        service_code = str(row['SERVICE CODE']).strip()
                        service_name = str(row['SERVICE NAME']).strip()
                        
                        # Parse amount
                        try:
                            amount = Decimal(str(row['AMOUNT']))
                        except (InvalidOperation, ValueError):
                            stats['errors'].append(
                                f"Row {index + 2}: Invalid amount '{row['AMOUNT']}'"
                            )
                            stats['skipped'] += 1
                            continue
                        
                        # Get description if available
                        description = ''
                        if 'DESCRIPTION' in df.columns:
                            description = str(row['DESCRIPTION']).strip() if pd.notna(row['DESCRIPTION']) else ''
                        
                        # Validate department
                        if department not in DEPARTMENT_MODELS:
                            stats['errors'].append(
                                f"Row {index + 2}: Invalid department '{department}'. "
                                f"Must be one of: {', '.join(DEPARTMENT_MODELS.keys())}"
                            )
                            stats['skipped'] += 1
                            continue
                        
                        # Validate required fields
                        if not service_code:
                            stats['errors'].append(f"Row {index + 2}: Service code is required")
                            stats['skipped'] += 1
                            continue
                        
                        if not service_name:
                            stats['errors'].append(f"Row {index + 2}: Service name is required")
                            stats['skipped'] += 1
                            continue
                        
                        if amount <= 0:
                            stats['errors'].append(
                                f"Row {index + 2}: Amount must be greater than zero"
                            )
                            stats['skipped'] += 1
                            continue
                        
                        # Get model for department
                        Model = DEPARTMENT_MODELS[department]
                        
                        # Check if service already exists
                        existing = Model.objects.filter(service_code=service_code).first()
                        
                        if existing:
                            if update_existing:
                                existing.service_name = service_name
                                existing.amount = amount
                                existing.description = description
                                existing.is_active = True
                                existing.save()
                                stats['updated'] += 1
                            else:
                                stats['skipped'] += 1
                        else:
                            Model.objects.create(
                                service_code=service_code,
                                service_name=service_name,
                                amount=amount,
                                description=description,
                                is_active=True
                            )
                            stats['created'] += 1
                    
                    except Exception as e:
                        stats['errors'].append(f"Row {index + 2}: {str(e)}")
                        stats['skipped'] += 1
            
            # Audit log
            user_role = getattr(request.user, 'role', None) or \
                       getattr(request.user, 'get_role', lambda: None)()
            AuditLog.log(
                user=request.user,
                role=user_role,
                action="SERVICES_IMPORTED",
                resource_type="service_catalog",
                resource_id=None,
                request=request,
                metadata={
                    'file_name': uploaded_file.name,
                    'total': stats['total'],
                    'created': stats['created'],
                    'updated': stats['updated'],
                    'skipped': stats['skipped'],
                    'errors_count': len(stats['errors']),
                }
            )
            
            # Prepare response
            if stats['errors']:
                message = (
                    f"Import completed with {len(stats['errors'])} errors. "
                    f"Created: {stats['created']}, Updated: {stats['updated']}, Skipped: {stats['skipped']}"
                )
            else:
                message = (
                    f"Successfully imported {stats['created']} services. "
                    f"Updated: {stats['updated']}, Skipped: {stats['skipped']}"
                )
            
            return Response({
                'success': True,
                'message': message,
                'stats': stats,
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error importing services: {str(e)}',
                'stats': stats,
            }, status=status.HTTP_400_BAD_REQUEST)


"""
Web API for importing Service Catalog from Excel or CSV files.
Upload Excel/CSV → merge with existing ServiceCatalog (create new, update existing by service_code).
"""
import pandas as pd
from io import BytesIO
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.exceptions import ValidationError as DRFValidationError

from .service_catalog_import import import_services


class ServiceCatalogImportView(APIView):
    """
    POST /api/v1/billing/service-catalog/import/

    Upload Excel or CSV file to import/merge services into ServiceCatalog.
    - New services (by service_code) → created
    - Existing services (with update=true) → updated

    Request: multipart/form-data
    - file: Excel (.xlsx, .xls) or CSV (.csv)
    - update: true|false (default: false) — update existing services by service_code
    - sheet: Sheet name or index (default: 0) — Excel only
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        if 'file' not in request.FILES:
            raise DRFValidationError("No file uploaded. Please provide an Excel (.xlsx, .xls) or CSV (.csv) file.")

        uploaded_file = request.FILES['file']
        name = (uploaded_file.name or '').lower()
        valid_extensions = ('.xlsx', '.xls', '.csv')
        if not any(name.endswith(ext) for ext in valid_extensions):
            raise DRFValidationError(
                f"Invalid file type. Upload Excel (.xlsx, .xls) or CSV (.csv). Received: {uploaded_file.name}"
            )

        max_size = 10 * 1024 * 1024  # 10MB
        if uploaded_file.size > max_size:
            raise DRFValidationError(
                f"File too large. Max 10MB. Received: {uploaded_file.size / 1024 / 1024:.2f} MB"
            )

        update_existing = request.data.get('update', 'false').lower() == 'true'
        sheet = request.data.get('sheet', 0)
        if isinstance(sheet, str) and sheet.isdigit():
            sheet = int(sheet)

        try:
            content = uploaded_file.read()
            if name.endswith('.csv'):
                try:
                    df = pd.read_csv(BytesIO(content), encoding='utf-8', sep=None, engine='python')
                except UnicodeDecodeError:
                    df = pd.read_csv(BytesIO(content), encoding='latin-1', sep=None, engine='python')
            else:
                df = pd.read_excel(BytesIO(content), sheet_name=sheet)
        except Exception as e:
            raise DRFValidationError(f"Error reading file: {str(e)}")

        df.columns = df.columns.astype(str).str.strip().str.lower()
        data = df.to_dict('records')

        if not data:
            raise DRFValidationError("File has no data rows.")

        stats = import_services(data, update_existing=update_existing, dry_run=False)

        msg = (
            f"Created: {stats['created']}, Updated: {stats['updated']}, Skipped: {stats['skipped']}"
            + (f". Errors: {len(stats['errors'])}" if stats['errors'] else "")
        )
        return Response({
            'success': True,
            'message': msg,
            'stats': stats,
        }, status=status.HTTP_200_OK)

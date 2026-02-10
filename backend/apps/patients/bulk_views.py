"""
Bulk operations views for patient management.

Endpoint: /api/v1/patients/bulk/

Enforcement:
1. Receptionist-only access
2. Audit logging mandatory
3. PHI data protection
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.http import HttpResponse
from django.db.models import Q

from .models import Patient
from .bulk_operations import (
    import_patients_from_csv,
    export_patients_to_csv,
    export_patients_to_json,
)
from .permissions import CanManagePatients


class PatientBulkViewSet(viewsets.ViewSet):
    """
    ViewSet for bulk patient operations.
    
    Endpoint: /api/v1/patients/bulk/
    """
    permission_classes = [IsAuthenticated, CanManagePatients]
    
    @action(detail=False, methods=['post'], url_path='import-csv')
    def import_csv(self, request):
        """
        Import patients from CSV file.
        
        POST /api/v1/patients/bulk/import-csv/
        
        Body:
        {
            "csv_content": "first_name,last_name,...\nJohn,Doe,..."
        }
        """
        csv_content = request.data.get('csv_content')
        
        if not csv_content:
            return Response(
                {'error': 'csv_content is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = import_patients_from_csv(
                csv_content=csv_content,
                created_by=request.user,
                request=request
            )
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'], url_path='export-csv')
    def export_csv(self, request):
        """
        Export patients to CSV file.
        
        GET /api/v1/patients/bulk/export-csv/
        
        Query params:
        - search: Search term
        - is_active: Filter by active status
        """
        queryset = Patient.objects.all()
        
        # Apply filters
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(patient_id__icontains=search) |
                Q(national_id__icontains=search)
            )
        
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Generate CSV
        csv_content = export_patients_to_csv(queryset)
        
        # Create HTTP response
        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="patients_export.csv"'
        
        return response
    
    @action(detail=False, methods=['get'], url_path='export-json')
    def export_json(self, request):
        """
        Export patients to JSON file.
        
        GET /api/v1/patients/bulk/export-json/
        
        Query params:
        - search: Search term
        - is_active: Filter by active status
        """
        queryset = Patient.objects.all()
        
        # Apply filters
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(patient_id__icontains=search) |
                Q(national_id__icontains=search)
            )
        
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Generate JSON
        json_content = export_patients_to_json(queryset)
        
        # Create HTTP response
        response = HttpResponse(json_content, content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="patients_export.json"'
        
        return response

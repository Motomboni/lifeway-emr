"""
Views for document management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.http import FileResponse
import os

from .models import MedicalDocument
from .serializers import MedicalDocumentSerializer, MedicalDocumentCreateSerializer
from .permissions import CanManageDocuments, CanViewDocuments
from apps.visits.models import Visit
from core.permissions import IsVisitOpen, IsVisitAccessible
from core.audit import AuditLog


def log_document_action(user, action, visit_id, document_id, request=None):
    """Log document action to audit log."""
    user_role = getattr(user, 'role', None) or \
               getattr(user, 'get_role', lambda: None)()
    if not user_role:
        user_role = 'UNKNOWN'
    
    AuditLog.log(
        user=user,
        role=user_role,
        action=f"DOCUMENT_{action}",
        visit_id=visit_id,
        resource_type='medical_document',
        resource_id=document_id,
        request=request,
    )


class MedicalDocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Medical Documents.
    
    Rules enforced:
    - Visit-scoped
    - Doctor/Receptionist can upload
    - All authenticated users can view
    - Soft delete only (immutability)
    """
    serializer_class = MedicalDocumentSerializer
    permission_classes = [CanViewDocuments]
    pagination_class = None
    
    def get_queryset(self):
        """Get documents for the visit (excluding soft-deleted)."""
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            return MedicalDocument.objects.none()
        
        queryset = MedicalDocument.objects.filter(
            visit_id=visit_id,
            is_deleted=False
        ).select_related('visit', 'uploaded_by', 'deleted_by')
        
        return queryset
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return MedicalDocumentCreateSerializer
        return MedicalDocumentSerializer
    
    def get_permissions(self):
        """Override permissions based on action."""
        if self.action in ['create', 'destroy']:
            return [CanManageDocuments(), IsVisitOpen()]
        return [CanViewDocuments(), IsVisitAccessible()]
    
    def perform_create(self, serializer):
        """Create document with visit-scoped enforcement."""
        visit_id = self.kwargs.get('visit_id')
        visit = get_object_or_404(Visit, pk=visit_id)
        
        # Ensure visit is OPEN
        if visit.status == 'CLOSED':
            raise PermissionDenied("Cannot upload documents for a CLOSED visit.")
        
        document = serializer.save(
            visit=visit,
            uploaded_by=self.request.user
        )
        
        # Audit log
        log_document_action(
            user=self.request.user,
            action='UPLOADED',
            visit_id=visit.id,
            document_id=document.id,
            request=self.request,
        )
        
        return document
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete document (cannot be permanently deleted)."""
        document = self.get_object()
        
        # Check permission
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        if user_role not in ['DOCTOR', 'RECEPTIONIST']:
            raise PermissionDenied("Only doctors and receptionists can delete documents.")
        
        # Soft delete
        document.soft_delete(request.user)
        
        # Audit log
        log_document_action(
            user=request.user,
            action='DELETED',
            visit_id=document.visit_id,
            document_id=document.id,
            request=request,
        )
        
        return Response(
            {'message': 'Document deleted successfully'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['get'], url_path='download')
    def download_document(self, request, pk=None, visit_id=None):
        """Download document file."""
        document = self.get_object()
        
        if not document.file:
            return Response(
                {'error': 'Document file not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Audit log for download
        log_document_action(
            user=request.user,
            action='DOWNLOADED',
            visit_id=document.visit_id,
            document_id=document.id,
            request=request,
        )
        
        # Return file response
        response = FileResponse(
            document.file.open('rb'),
            content_type=document.mime_type or 'application/octet-stream'
        )
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(document.file.name)}"'
        return response

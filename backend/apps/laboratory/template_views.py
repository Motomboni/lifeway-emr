"""
Views for Lab Test Templates.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
import logging

from .template_models import LabTestTemplate
from .template_serializers import (
    LabTestTemplateSerializer,
    LabTestTemplateCreateSerializer,
)
from core.audit import AuditLog

logger = logging.getLogger(__name__)


class LabTestTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Lab Test Templates.
    
    Rules enforced:
    - Doctor-only access for create/update/delete
    - All authenticated users can view templates
    - Templates can be used by all doctors
    """
    queryset = LabTestTemplate.objects.filter(is_active=True).select_related('created_by')
    serializer_class = LabTestTemplateSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Disable pagination for templates (small lists)
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return LabTestTemplateCreateSerializer
        return LabTestTemplateSerializer
    
    def get_permissions(self):
        """Override to allow read access for all authenticated users."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Only doctors can create/edit templates
            from core.permissions import IsDoctor
            return [IsDoctor()]
        else:
            # All authenticated users can view templates
            return [IsAuthenticated()]
    
    def list(self, request, *args, **kwargs):
        """List all lab test templates with error handling."""
        try:
            return super().list(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error listing lab test templates: {str(e)}", exc_info=True)
            return Response(
                {'detail': f'Error loading templates: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def perform_create(self, serializer):
        """Create lab test template."""
        template = serializer.save(created_by=self.request.user)
        
        # Audit log
        user_role = getattr(self.request.user, 'role', None) or 'UNKNOWN'
        AuditLog.log(
            user=self.request.user,
            role=user_role,
            action='LAB_TEST_TEMPLATE_CREATED',
            resource_type='lab_test_template',
            resource_id=template.id,
            request=self.request,
        )
        
        return template
    
    def perform_update(self, serializer):
        """Update lab test template."""
        template = serializer.save()
        
        # Audit log
        user_role = getattr(self.request.user, 'role', None) or 'UNKNOWN'
        AuditLog.log(
            user=self.request.user,
            role=user_role,
            action='LAB_TEST_TEMPLATE_UPDATED',
            resource_type='lab_test_template',
            resource_id=template.id,
            request=self.request,
        )
        
        return template
    
    @action(detail=True, methods=['post'], url_path='use')
    def use_template(self, request, pk=None):
        """
        Use a template and increment usage count.
        
        Returns the template data that can be used to create a lab order.
        """
        template = self.get_object()
        template.increment_usage()
        
        return Response({
            'tests': template.tests,
            'clinical_indication': template.default_clinical_indication or '',
        })


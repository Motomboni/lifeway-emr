"""
Views for Radiology Test Templates.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
import logging

from .template_models import RadiologyTestTemplate
from .template_serializers import (
    RadiologyTestTemplateSerializer,
    RadiologyTestTemplateCreateSerializer,
)
from core.audit import AuditLog

logger = logging.getLogger(__name__)


class RadiologyTestTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Radiology Test Templates.
    
    Rules enforced:
    - Doctor-only access for create/update/delete
    - All authenticated users can view templates
    - Templates can be used by all doctors
    """
    queryset = RadiologyTestTemplate.objects.filter(is_active=True).select_related('created_by')
    serializer_class = RadiologyTestTemplateSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Disable pagination for templates (small lists)
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return RadiologyTestTemplateCreateSerializer
        return RadiologyTestTemplateSerializer
    
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
        """List all radiology test templates with error handling."""
        try:
            return super().list(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error listing radiology test templates: {str(e)}", exc_info=True)
            return Response(
                {'detail': f'Error loading templates: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def perform_create(self, serializer):
        """Create radiology test template."""
        template = serializer.save(created_by=self.request.user)
        
        # Audit log
        user_role = getattr(self.request.user, 'role', None) or 'UNKNOWN'
        AuditLog.log(
            user=self.request.user,
            role=user_role,
            action='RADIOLOGY_TEST_TEMPLATE_CREATED',
            resource_type='radiology_test_template',
            resource_id=template.id,
            request=self.request,
        )
        
        return template
    
    def perform_update(self, serializer):
        """Update radiology test template."""
        template = serializer.save()
        
        # Audit log
        user_role = getattr(self.request.user, 'role', None) or 'UNKNOWN'
        AuditLog.log(
            user=self.request.user,
            role=user_role,
            action='RADIOLOGY_TEST_TEMPLATE_UPDATED',
            resource_type='radiology_test_template',
            resource_id=template.id,
            request=self.request,
        )
        
        return template
    
    @action(detail=True, methods=['post'], url_path='use')
    def use_template(self, request, pk=None):
        """
        Use a template and increment usage count.
        
        Returns the template data that can be used to create a radiology order.
        """
        template = self.get_object()
        template.increment_usage()
        
        return Response({
            'imaging_type': template.imaging_type,
            'body_part': template.body_part,
            'study_code': template.study_code or '',
            'clinical_indication': template.default_clinical_indication or '',
            'priority': template.default_priority,
        })


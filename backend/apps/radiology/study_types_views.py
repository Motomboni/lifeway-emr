"""
Views for Radiology Study Types Catalog.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.db.models import Q
from .study_types_models import RadiologyStudyType
from .study_types_serializers import (
    RadiologyStudyTypeSerializer,
    RadiologyStudyTypeCreateSerializer,
)
from .study_types_permissions import CanManageRadiologyStudyTypes, CanViewRadiologyStudyTypes
from core.audit import AuditLog


def log_radiology_study_type_action(
    user,
    action,
    study_type_id=None,
    request=None,
    metadata=None
):
    """
    Log a radiology study type catalog action to audit log.
    
    Args:
        user: User performing the action
        action: Action type (e.g., 'create', 'update', 'read')
        study_type_id: Radiology Study Type ID if applicable
        request: Django request object (for IP/user agent)
        metadata: Additional metadata dict (no PHI)
    
    Returns:
        AuditLog instance
    """
    user_role = getattr(user, 'role', None) or getattr(user, 'get_role', lambda: 'UNKNOWN')()
    
    ip_address = None
    user_agent = ''
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
    
    audit_log = AuditLog(
        user=user,
        user_role=user_role,
        action=f'radiology_study_type.{action}',
        visit_id=None,  # Catalog is not visit-scoped
        resource_type='radiology_study_type',
        resource_id=study_type_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata or {}
    )
    audit_log.save()
    return audit_log


class RadiologyStudyTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Radiology Study Types Catalog management.
    
    Rules enforced:
    - Global endpoint (not visit-scoped)
    - Doctors and Radiology Techs can manage
    - All authenticated users can view
    - Audit logging
    """
    
    queryset = RadiologyStudyType.objects.all().select_related('created_by')
    pagination_class = None  # Disable pagination for catalog
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return RadiologyStudyTypeCreateSerializer
        else:
            return RadiologyStudyTypeSerializer
    
    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        
        - Create/Update/Delete: Doctors and Radiology Techs
        - Read: All authenticated users
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [CanManageRadiologyStudyTypes]
        else:
            permission_classes = [CanViewRadiologyStudyTypes]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filter queryset based on query parameters."""
        queryset = super().get_queryset()
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filter by contrast required
        contrast_required = self.request.query_params.get('contrast_required')
        if contrast_required is not None:
            queryset = queryset.filter(contrast_required=contrast_required.lower() == 'true')
        
        # Search by code or name
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(study_code__icontains=search) |
                Q(study_name__icontains=search) |
                Q(description__icontains=search) |
                Q(body_part__icontains=search)
            )
        
        return queryset.order_by('category', 'study_name')
    
    def perform_create(self, serializer):
        """Create radiology study type catalog entry with audit logging."""
        study_type = serializer.save()
        
        # Audit log
        log_radiology_study_type_action(
            user=self.request.user,
            action='create',
            study_type_id=study_type.id,
            request=self.request,
            metadata={
                'study_code': study_type.study_code,
                'study_name': study_type.study_name,
                'category': study_type.category,
            }
        )
        
        return study_type
    
    def perform_update(self, serializer):
        """Update radiology study type catalog entry with audit logging."""
        study_type = serializer.save()
        
        # Audit log
        log_radiology_study_type_action(
            user=self.request.user,
            action='update',
            study_type_id=study_type.id,
            request=self.request,
            metadata={
                'study_code': study_type.study_code,
                'updated_fields': list(serializer.validated_data.keys()),
            }
        )
        
        return study_type
    
    def perform_destroy(self, instance):
        """Delete radiology study type catalog entry with audit logging."""
        study_type_id = instance.id
        study_code = instance.study_code
        
        # Audit log before deletion
        log_radiology_study_type_action(
            user=self.request.user,
            action='delete',
            study_type_id=study_type_id,
            request=self.request,
            metadata={
                'study_code': study_code,
            }
        )
        
        instance.delete()
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a radiology study type catalog entry."""
        study_type = self.get_object()
        
        # Audit log
        log_radiology_study_type_action(
            user=request.user,
            action='read',
            study_type_id=study_type.id,
            request=request,
        )
        
        serializer = self.get_serializer(study_type)
        return Response(serializer.data)
    
    def list(self, request, *args, **kwargs):
        """List radiology study type catalog entries."""
        # Audit log
        log_radiology_study_type_action(
            user=request.user,
            action='list',
            request=request,
        )
        
        return super().list(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'], url_path='categories')
    def categories(self, request):
        """Get list of available categories."""
        categories = RadiologyStudyType.objects.values_list('category', flat=True).distinct()
        return Response({
            'categories': sorted(list(set(categories)))
        })
    
    @action(detail=False, methods=['get'], url_path='active')
    def active_study_types(self, request):
        """Get only active radiology study types."""
        active_study_types = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(active_study_types, many=True)
        return Response(serializer.data)

"""
Views for Lab Test Catalog.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.db.models import Q
from .catalog_models import LabTestCatalog
from .catalog_serializers import (
    LabTestCatalogSerializer,
    LabTestCatalogCreateSerializer,
)
from .catalog_permissions import CanManageLabTestCatalog, CanViewLabTestCatalog
from core.audit import AuditLog


def log_lab_catalog_action(
    user,
    action,
    test_id=None,
    request=None,
    metadata=None
):
    """
    Log a lab test catalog action to audit log.
    
    Args:
        user: User performing the action
        action: Action type (e.g., 'create', 'update', 'read')
        test_id: Lab Test Catalog ID if applicable
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
        action=f'lab_test_catalog.{action}',
        visit_id=None,  # Catalog is not visit-scoped
        resource_type='lab_test_catalog',
        resource_id=test_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata or {}
    )
    audit_log.save()
    return audit_log


class LabTestCatalogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Lab Test Catalog management.
    
    Rules enforced:
    - Global endpoint (not visit-scoped)
    - Doctors and Lab Techs can manage
    - All authenticated users can view
    - Audit logging
    """
    
    queryset = LabTestCatalog.objects.all().select_related('created_by')
    pagination_class = None  # Disable pagination for catalog
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return LabTestCatalogCreateSerializer
        else:
            return LabTestCatalogSerializer
    
    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        
        - Create/Update/Delete: Doctors and Lab Techs
        - Read: All authenticated users
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [CanManageLabTestCatalog]
        else:
            permission_classes = [CanViewLabTestCatalog]
        
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
        
        # Search by code or name
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(test_code__icontains=search) |
                Q(test_name__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.order_by('category', 'test_name')
    
    def perform_create(self, serializer):
        """Create lab test catalog entry with audit logging."""
        test = serializer.save()
        
        # Audit log
        log_lab_catalog_action(
            user=self.request.user,
            action='create',
            test_id=test.id,
            request=self.request,
            metadata={
                'test_code': test.test_code,
                'test_name': test.test_name,
                'category': test.category,
            }
        )
        
        return test
    
    def perform_update(self, serializer):
        """Update lab test catalog entry with audit logging."""
        test = serializer.save()
        
        # Audit log
        log_lab_catalog_action(
            user=self.request.user,
            action='update',
            test_id=test.id,
            request=self.request,
            metadata={
                'test_code': test.test_code,
                'updated_fields': list(serializer.validated_data.keys()),
            }
        )
        
        return test
    
    def perform_destroy(self, instance):
        """Delete lab test catalog entry with audit logging."""
        test_id = instance.id
        test_code = instance.test_code
        
        # Audit log before deletion
        log_lab_catalog_action(
            user=self.request.user,
            action='delete',
            test_id=test_id,
            request=self.request,
            metadata={
                'test_code': test_code,
            }
        )
        
        instance.delete()
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a lab test catalog entry."""
        test = self.get_object()
        
        # Audit log
        log_lab_catalog_action(
            user=request.user,
            action='read',
            test_id=test.id,
            request=request,
        )
        
        serializer = self.get_serializer(test)
        return Response(serializer.data)
    
    def list(self, request, *args, **kwargs):
        """List lab test catalog entries."""
        # Audit log
        log_lab_catalog_action(
            user=request.user,
            action='list',
            request=request,
        )
        
        return super().list(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'], url_path='categories')
    def categories(self, request):
        """Get list of available categories."""
        categories = LabTestCatalog.objects.values_list('category', flat=True).distinct()
        return Response({
            'categories': sorted(list(set(categories)))
        })
    
    @action(detail=False, methods=['get'], url_path='active')
    def active_tests(self, request):
        """Get only active lab tests."""
        active_tests = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(active_tests, many=True)
        return Response(serializer.data)

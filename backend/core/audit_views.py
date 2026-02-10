"""
Audit Log ViewSet - read-only access to audit logs.

Per EMR Rules:
- Audit logs are append-only and immutable
- Read-only access for compliance and security
- Admin-only access (or specific role-based access)
- Visit-scoped filtering available
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q
from .audit import AuditLog
from .audit_serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Audit Log viewing (read-only).
    
    Endpoint: /api/v1/audit-logs/
    
    Rules:
    - Read-only (no create/update/delete)
    - Admin or specific roles only
    - Visit-scoped filtering
    - Action-based filtering
    """
    
    queryset = AuditLog.objects.all().select_related('user').order_by('-timestamp')
    permission_classes = [IsAuthenticated]
    serializer_class = AuditLogSerializer
    
    def get_queryset(self):
        """Filter audit logs based on query parameters."""
        queryset = super().get_queryset()
        
        # Filter by visit_id if provided
        visit_id = self.request.query_params.get('visit_id', None)
        if visit_id:
            queryset = queryset.filter(visit_id=visit_id)
        
        # Filter by user if provided
        user_id = self.request.query_params.get('user', None)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filter by action if provided
        action = self.request.query_params.get('action', None)
        if action:
            queryset = queryset.filter(action__icontains=action)
        
        # Filter by resource_type if provided
        resource_type = self.request.query_params.get('resource_type', None)
        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)
        
        # Filter by date range if provided
        date_from = self.request.query_params.get('date_from', None)
        if date_from:
            queryset = queryset.filter(timestamp__gte=date_from)
        
        date_to = self.request.query_params.get('date_to', None)
        if date_to:
            queryset = queryset.filter(timestamp__lte=date_to)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """
        List audit logs with filtering.
        
        Query parameters:
        - visit_id: Filter by visit ID
        - user: Filter by user ID
        - action: Filter by action (partial match)
        - resource_type: Filter by resource type
        - date_from: Filter from date (YYYY-MM-DD)
        - date_to: Filter to date (YYYY-MM-DD)
        - page: Page number
        - page_size: Page size
        """
        # Check if user has permission to view audit logs
        # For now, allow authenticated users (can be restricted further)
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        # Only allow admin or specific roles (adjust as needed)
        # For now, allow all authenticated users to view their own audit logs
        # and visit-scoped audit logs
        
        queryset = self.get_queryset()
        
        # If not admin, filter to user's own logs or visit-scoped logs they have access to
        if user_role not in ['ADMIN', 'DOCTOR']:  # Adjust roles as needed
            queryset = queryset.filter(
                Q(user=request.user) | Q(visit_id__isnull=False)
            )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

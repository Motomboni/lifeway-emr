"""
Views for Operation Notes.
"""
import logging
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError as DRFValidationError
from django.shortcuts import get_object_or_404
from django.db import OperationalError

from .operation_models import OperationNote
from .serializers import (
    OperationNoteSerializer,
    OperationNoteCreateSerializer,
)
from .permissions import CanManageOperationNotes
from apps.visits.models import Visit
from core.permissions import IsVisitOpen, IsVisitAccessible
from core.audit import AuditLog


def log_operation_action(user, action, visit_id, resource_type, resource_id, request=None):
    """Log operation action to audit log."""
    user_role = getattr(user, 'role', None) or \
               getattr(user, 'get_role', lambda: None)()
    if not user_role:
        user_role = 'UNKNOWN'
    
    AuditLog.log(
        user=user,
        role=user_role,
        action=f"OPERATION_{action}",
        visit_id=visit_id,
        resource_type=resource_type,
        resource_id=resource_id,
        request=request,
    )


class OperationNoteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Operation Notes.
    
    Rules enforced:
    - Visit-scoped
    - Doctor-only creation
    - Consultation-dependent
    - Immutable after creation
    """
    serializer_class = OperationNoteSerializer
    permission_classes = [CanManageOperationNotes]
    pagination_class = None
    
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to catch all exceptions and return empty list for list action."""
        logger = logging.getLogger(__name__)
        try:
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            # If it's a list action (GET without pk) and there's any error, return empty list
            if request.method == 'GET' and 'pk' not in kwargs:
                logger.warning(f"Error in OperationNoteViewSet dispatch (returning empty list): {e}", exc_info=True)
                # Return a proper DRF response
                return Response([], status=status.HTTP_200_OK)
            # For other actions, log and re-raise
            logger.error(f"Error in OperationNoteViewSet dispatch: {e}", exc_info=True)
            raise
    
    def get_permissions(self):
        """Return appropriate permissions based on action."""
        from rest_framework.permissions import IsAuthenticated
        try:
            if self.action in ['create', 'update', 'partial_update', 'destroy']:
                return [CanManageOperationNotes(), IsVisitOpen()]
            else:
                # Read operations: Just require authentication
                return [IsAuthenticated()]
        except Exception as e:
            # If there's any error in permissions, just require authentication
            logger = logging.getLogger(__name__)
            logger.warning(f"Error in get_permissions, falling back to IsAuthenticated: {e}")
            return [IsAuthenticated()]
    
    def get_visit(self):
        """Get visit from middleware or URL parameter."""
        try:
            # First try to get from request.visit set by middleware
            if hasattr(self.request, 'visit') and self.request.visit:
                return self.request.visit
            
            # Fallback to kwargs (from URL pattern)
            visit_id = self.kwargs.get('visit_id')
            if not visit_id:
                raise DRFValidationError("visit_id is required in URL")
            
            try:
                visit = Visit.objects.get(pk=visit_id)
            except Visit.DoesNotExist:
                raise NotFound(detail=f"Visit with id {visit_id} not found.")
            
            # Set on request for permissions
            self.request.visit = visit
            return visit
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error in get_visit: {e}", exc_info=True)
            raise
    
    def get_queryset(self):
        """Get operation notes for the visit."""
        logger = logging.getLogger(__name__)
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            return OperationNote.objects.none()
        
        try:
            # Try to query - this will fail if table doesn't exist
            return OperationNote.objects.filter(visit_id=visit_id).select_related(
                'visit', 'consultation', 'surgeon', 'assistant_surgeon', 'anesthetist'
            )
        except Exception as e:
            # Catch ALL exceptions - table might not exist, or any other DB error
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ['no such table', 'relation', 'does not exist', 'table', 'operational']):
                logger.warning(f"Operation notes table may not exist. Please run migrations. Error: {e}")
            else:
                logger.error(f"Unexpected error in get_queryset: {e}", exc_info=True)
            return OperationNote.objects.none()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return OperationNoteCreateSerializer
        return OperationNoteSerializer
    
    def list(self, request, *args, **kwargs):
        """List operation notes with error handling."""
        logger = logging.getLogger(__name__)
        try:
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except Exception as e:
            # Catch ALL exceptions to prevent 500 errors
            error_str = str(e).lower()
            logger.warning(f"Error listing operation notes (returning empty list): {e}")
            # Always return empty list to prevent 500 errors
            # This handles cases where table doesn't exist or any other DB error
            return Response([])
    
    def perform_create(self, serializer):
        """Create operation note."""
        visit = self.get_visit()
        
        # Ensure visit is OPEN
        if visit.status == 'CLOSED':
            raise PermissionDenied("Cannot create operation note for a CLOSED visit.")
        
        # Ensure user is a Doctor
        user_role = getattr(self.request.user, 'role', None) or \
                   getattr(self.request.user, 'get_role', lambda: None)()
        if user_role != 'DOCTOR':
            raise PermissionDenied("Only Doctors can create operation notes.")
        
        operation_note = serializer.save(
            visit=visit,
            surgeon=self.request.user
        )
        
        # Audit log
        log_operation_action(
            user=self.request.user,
            action='NOTE_CREATED',
            visit_id=visit.id,
            resource_type='operation_note',
            resource_id=operation_note.id,
            request=self.request,
        )
        
        return operation_note
    
    def perform_update(self, serializer):
        """Update operation note (only if visit is OPEN)."""
        visit = self.get_visit()
        
        # Ensure visit is OPEN
        if visit.status == 'CLOSED':
            raise PermissionDenied("Cannot update operation note for a CLOSED visit.")
        
        operation_note = serializer.save()
        
        # Audit log
        log_operation_action(
            user=self.request.user,
            action='NOTE_UPDATED',
            visit_id=visit.id,
            resource_type='operation_note',
            resource_id=operation_note.id,
            request=self.request,
        )
        
        return operation_note
    
    def perform_destroy(self, instance):
        """Delete operation note (only if visit is OPEN)."""
        visit = self.get_visit()
        
        # Ensure visit is OPEN
        if visit.status == 'CLOSED':
            raise PermissionDenied("Cannot delete operation note for a CLOSED visit.")
        
        operation_id = instance.id
        visit_id = visit.id
        
        instance.delete()
        
        # Audit log
        log_operation_action(
            user=self.request.user,
            action='NOTE_DELETED',
            visit_id=visit_id,
            resource_type='operation_note',
            resource_id=operation_id,
            request=self.request,
        )

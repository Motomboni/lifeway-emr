"""
Backup and Restore ViewSets.

Endpoint: /api/v1/backups/

Enforcement:
1. Superuser-only access
2. Audit logging mandatory
3. Backup files encrypted
4. Restore operations tracked
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from django.db import transaction

from .models import Backup, Restore
from .serializers import (
    BackupSerializer,
    BackupCreateSerializer,
    RestoreSerializer,
    RestoreCreateSerializer,
)
from .permissions import CanManageBackups
from .utils import create_backup_file, restore_from_backup


def log_backup_action(
    user,
    action,
    backup_id,
    request=None,
    metadata=None
):
    """
    Log a backup action to audit log.
    """
    from core.audit import AuditLog
    
    user_role = getattr(user, 'role', None)
    if not user_role:
        user_role = getattr(user, 'get_role', lambda: None)()
    if not user_role:
        user_role = 'UNKNOWN'
    
    ip_address = None
    user_agent = ''
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
    
    AuditLog.log(
        user=user,
        role=user_role,
        action=f'BACKUP_{action.upper()}',
        resource_type='backup',
        resource_id=backup_id,
        request=request,
        metadata=metadata or {}
    )


class BackupViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Backup management.
    
    Rules enforced:
    - Superuser-only access
    - Audit logging
    - Backup file creation
    """
    
    queryset = Backup.objects.all().select_related('created_by')
    permission_classes = [CanManageBackups]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return BackupCreateSerializer
        return BackupSerializer
    
    def perform_create(self, serializer):
        """Create backup record and initiate backup process."""
        backup = serializer.save(
            created_by=self.request.user,
            status='PENDING'
        )
        
        log_backup_action(
            user=self.request.user,
            action='create',
            backup_id=backup.id,
            request=self.request,
            metadata={
                'backup_type': backup.backup_type,
            }
        )
        
        # Start backup process (async in production, sync for now)
        try:
            backup.status = 'IN_PROGRESS'
            backup.started_at = timezone.now()
            backup.save(update_fields=['status', 'started_at'])
            
            # Create backup file
            create_backup_file(backup)
            
            backup.status = 'COMPLETED'
            backup.completed_at = timezone.now()
            backup.save(update_fields=['status', 'completed_at'])
            
        except Exception as e:
            backup.status = 'FAILED'
            backup.completed_at = timezone.now()
            backup.error_message = str(e)
            backup.save(update_fields=['status', 'completed_at', 'error_message'])
            raise
        
        return backup
    
    @action(detail=True, methods=['post'])
    def download(self, request, pk=None):
        """Download backup file."""
        backup = self.get_object()
        
        if backup.status != 'COMPLETED':
            return Response(
                {'error': 'Backup is not completed.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not backup.file_path or not os.path.exists(backup.file_path):
            return Response(
                {'error': 'Backup file not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        log_backup_action(
            user=request.user,
            action='download',
            backup_id=backup.id,
            request=request,
        )
        
        from django.http import FileResponse
        
        response = FileResponse(
            open(backup.file_path, 'rb'),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="backup_{backup.id}.json"'
        return response


class RestoreViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Restore management.
    
    Rules enforced:
    - Superuser-only access
    - Audit logging
    - Restore from completed backups only
    """
    
    queryset = Restore.objects.all().select_related('backup', 'created_by')
    permission_classes = [CanManageBackups]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return RestoreCreateSerializer
        return RestoreSerializer
    
    def perform_create(self, serializer):
        """Create restore record and initiate restore process."""
        restore = serializer.save(
            created_by=self.request.user,
            status='PENDING'
        )
        
        log_backup_action(
            user=self.request.user,
            action='restore_create',
            backup_id=restore.backup_id,
            request=self.request,
            metadata={
                'restore_id': restore.id,
            }
        )
        
        # Start restore process (async in production, sync for now)
        try:
            restore.status = 'IN_PROGRESS'
            restore.started_at = timezone.now()
            restore.save(update_fields=['status', 'started_at'])
            
            # Perform restore
            with transaction.atomic():
                result = restore_from_backup(restore)
            
            restore.status = 'COMPLETED'
            restore.completed_at = timezone.now()
            restore.save(update_fields=['status', 'completed_at'])
            
            log_backup_action(
                user=self.request.user,
                action='restore_completed',
                backup_id=restore.backup_id,
                request=self.request,
                metadata={
                    'restore_id': restore.id,
                    'items_restored': result.get('items_restored', 0),
                }
            )
            
        except Exception as e:
            restore.status = 'FAILED'
            restore.completed_at = timezone.now()
            restore.error_message = str(e)
            restore.save(update_fields=['status', 'completed_at', 'error_message'])
            
            log_backup_action(
                user=self.request.user,
                action='restore_failed',
                backup_id=restore.backup_id,
                request=self.request,
                metadata={
                    'restore_id': restore.id,
                    'error': str(e),
                }
            )
            raise
        
        return restore

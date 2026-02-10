"""
Backup Permissions - role-based access control.

Per EMR Rules:
- Only authorized users (typically admins or system administrators) can perform backups/restores
- For this implementation, we'll allow superusers and optionally a specific role
"""
from rest_framework import permissions


class CanManageBackups(permissions.BasePermission):
    """
    Permission for managing backups and restores.
    
    Only superusers or users with specific backup role can manage backups.
    For now, we'll allow superusers only (can be extended).
    """
    
    def has_permission(self, request, view):
        """Check if user has permission for backup operations."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Only superusers can manage backups (most secure)
        return request.user.is_superuser
    
    def has_object_permission(self, request, view, obj):
        """Check if user can perform action on specific backup/restore."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        return request.user.is_superuser

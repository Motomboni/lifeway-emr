"""
Permissions for document management.
"""
from rest_framework import permissions
from rest_framework.permissions import BasePermission


class CanManageDocuments(BasePermission):
    """Permission to manage documents (Doctors and Receptionists)."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        return user_role in ['DOCTOR', 'RECEPTIONIST']


class CanViewDocuments(BasePermission):
    """Permission to view documents (All authenticated users)."""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
